import base64
import csv
import io
from datetime import datetime, time

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SalesBidImportWizard(models.TransientModel):
    _name = "sales.bid.import.wizard"
    _description = "Import Sales Bids from CSV"

    data_file = fields.Binary(string="CSV File")
    filename = fields.Char(string="Filename")
    result_message = fields.Text(string="Import Result", readonly=True)

    # Expected CSV headers (case-insensitive match)
    REQUIRED_COLUMNS = {"project / client", "platform", "job url"}

    def action_download_template(self):
        """Download a sample CSV template."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Project / Client",
            "Platform",
            "Job URL",
            "Bid Amount",
            "Bid Type",
            "Bid Date",
            "Notes",
        ])
        writer.writerow([
            "Client ABC",
            "Upwork",
            "https://www.upwork.com/jobs/example",
            "500",
            "Fixed Price",
            "2026-09-03 10:00:00",
            "Optional notes",
        ])
        content = base64.b64encode(output.getvalue().encode("utf-8"))
        attachment = self.env["ir.attachment"].create({
            "name": "bid_import_template.csv",
            "type": "binary",
            "datas": content,
            "mimetype": "text/csv",
        })
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment.id}?download=true",
            "target": "self",
        }

    def action_import(self):
        self.ensure_one()
        if not self.data_file:
            raise UserError(_("Please upload a CSV file."))

        try:
            raw = base64.b64decode(self.data_file)
            text = raw.decode("utf-8-sig")  # handles Excel BOM
        except UnicodeDecodeError as err:
            raise UserError(_("File must be UTF-8 CSV.")) from err

        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames:
            raise UserError(_("CSV file has no headers."))

        # Normalize headers to lowercase for matching
        header_map = {h.strip().lower(): h for h in reader.fieldnames}

        missing = self.REQUIRED_COLUMNS - set(header_map)
        if missing:
            raise UserError(
                _("Missing required columns: %s") % ", ".join(sorted(missing))
            )

        created = 0
        errors = []

        for row_num, row in enumerate(reader, start=2):
            try:
                self._create_bid_from_row(row, header_map)
                created += 1
            except UserError as err:
                errors.append(_("Row %s: %s") % (row_num, err.args[0]))
            except Exception as err:
                errors.append(_("Row %s: %s") % (row_num, str(err)))

        message = _("Successfully imported %s bid(s).") % created
        if errors:
            message += "\n\n" + _("Errors:") + "\n" + "\n".join(errors)

        self.result_message = message

        if created and not errors:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Import Complete"),
                    "message": message,
                    "type": "success",
                    "sticky": False,
                    "next": {"type": "ir.actions.act_window_close"},
                },
            }

        # Show result in wizard if there were errors
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def _get_cell(self, row, header_map, column_name):
        key = column_name.lower()
        if key not in header_map:
            return ""
        return (row.get(header_map[key]) or "").strip()

    def _normalize_platform(self, value):
        value = value.lower()
        mapping = {
            "upwork": "upwork",
            "freelancer": "freelancer",
        }
        if value not in mapping:
            raise UserError(
                _("Invalid platform '%(val)s'. Use Upwork or Freelancer.", val=value)
            )
        return mapping[value]

    def _normalize_bid_type(self, value):
        value = value.lower().replace(" ", "_")
        mapping = {
            "fixed": "fixed",
            "fixed_price": "fixed",
            "hourly": "hourly",
        }
        if value not in mapping:
            raise UserError(
                _("Invalid bid type '%(val)s'. Use Fixed Price or Hourly.", val=value)
            )
        return mapping[value]

    def _parse_bid_date(self, value):
        if not value:
            bid_date = fields.Datetime.now()
        else:
            bid_date = None
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y %H:%M", "%d/%m/%Y"):
                try:
                    bid_date = datetime.strptime(value, fmt)
                    break
                except ValueError:
                    continue
            if bid_date is None:
                raise UserError(_("Invalid date format: %s") % value)
        if fields.Date.to_date(bid_date) > fields.Date.context_today(self):
            raise UserError(_("Bid date cannot be in the future."))
        return bid_date
        

    def _create_bid_from_row(self, row, header_map):
        name = self._get_cell(row, header_map, "project / client")
        platform_raw = self._get_cell(row, header_map, "platform")
        job_url = self._get_cell(row, header_map, "job url")

        if not name:
            raise UserError(_("Project / Client is required."))
        if not platform_raw:
            raise UserError(_("Platform is required."))
        if not job_url:
            raise UserError(_("Job URL is required."))

        amount_raw = self._get_cell(row, header_map, "bid amount")
        bid_type_raw = self._get_cell(row, header_map, "bid type") or "Fixed Price"
        bid_date_raw = self._get_cell(row, header_map, "bid date")
        notes = self._get_cell(row, header_map, "notes")

        vals = {
            "name": name,
            "platform": self._normalize_platform(platform_raw),
            "job_url": job_url,
            "bid_amount": float(amount_raw) if amount_raw else 0.0,
            "bid_type": self._normalize_bid_type(bid_type_raw),
            "status": "submitted",
            "bid_date": self._parse_bid_date(bid_date_raw),
            "notes": notes or False,
            "salesperson_id": self.env.user.id,  # always current bidder
        }

        self.env["sales.bid"].create(vals)