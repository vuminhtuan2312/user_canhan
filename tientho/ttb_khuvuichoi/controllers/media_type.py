from odoo import http
from odoo.exceptions import MissingError
from odoo.http import request

PROOF_MEDIA_MODELS = {
    "ttb.task.proof.image": "media_type",
    "ttb.post.audit.line": "proof_media_type",
}

class TtbMediaTypeController(http.Controller):
    @http.route("/web/binary/proof", type="http", auth="user")
    def proof_media(self, model, id, field, unique=None, **kwargs):
        try:
            res_id = int(id)
        except (TypeError, ValueError):
            raise MissingError("Invalid id")
        if model not in request.env:
            raise MissingError("Invalid model")
        if field not in request.env[model]._fields or request.env[model]._fields[field].type != "binary":
            raise MissingError("Invalid field")
        record = request.env[model].browse(res_id).exists()
        if not record:
            raise MissingError("Record not found")
        record.check_access_rights("read")
        record.check_access_rule("read")
        record.check_field_access_rights("read", [field])

        type_field = PROOF_MEDIA_MODELS.get(model)
        is_video = False
        if type_field and type_field in record._fields:
            try:
                is_video = (record[type_field] or "").strip() == "video"
            except Exception:
                pass

        default_mimetype = "video/webm" if is_video else "application/octet-stream"
        stream = request.env["ir.binary"]._get_stream_from(
            record, field_name=field, default_mimetype=default_mimetype
        )
        if not is_video and model == "ttb.task.proof.image":
            try:
                if stream.type == "data" and stream.data and len(stream.data) >= 2:
                    if stream.data[0:2] == b"\x1aE":
                        is_video = True
                elif stream.type == "path" and stream.path:
                    with open(stream.path, "rb") as f:
                        head = f.read(4)
                    if len(head) >= 2 and head[0:2] == b"\x1aE":
                        is_video = True
            except Exception:
                pass
        if is_video and stream.mimetype and not stream.mimetype.startswith("video/"):
            stream.mimetype = "video/webm"
        return stream.get_response()
