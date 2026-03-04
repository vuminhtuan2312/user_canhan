import json, requests, logging, inspect, datetime, time, decimal
from odoo import *
from lxml import etree
from xml.dom import minidom
import shlex

_logger = logging.getLogger(__name__)


def pretty_print_xml_minidom(xml_string):
    # Parse the XML string
    dom = minidom.parseString(xml_string)

    # Pretty print the XML
    pretty_xml = dom.toprettyxml(indent="  ")

    # Remove empty lines
    return "\n".join(line for line in pretty_xml.split("\n") if line.strip())


class JSONEncoder(json.JSONEncoder):
    def default(self, obj):  # pylint: disable=E0202,arguments-differ
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        elif isinstance(obj, datetime.date):
            return obj.isoformat()
        elif isinstance(obj, decimal.Decimal):
            return float(obj)
        elif isinstance(obj, set):
            return tuple(obj)
        return super(JSONEncoder, self).default(obj)


def json_dump(data):
    return json.dumps(data, cls=JSONEncoder, indent=4, sort_keys=True, ensure_ascii=False)


class ApiCallBase(models.AbstractModel):
    _name = 'api_call.base'
    _description = 'API Call Base'

    _log_api_call = True
    _log_call_stack = True
    _api_type = ''

    call_error = fields.Text(string="Lỗi đồng bộ", copy=False, readonly=True)
    call_log_ids = fields.One2many(string='API Logs', comodel_name='api_call.log', inverse_name='res_id', domain=lambda self: [('res_model', '=', self._name)])

    def to_curl(self, method, url, headers=None, data=None):
        cmd = ["curl", "-X", method]

        if headers:
            for k, v in headers.items():
                cmd.extend(["-H", f"{k}: {v}"])

        if data:
            cmd.extend(["--data-raw", data if isinstance(data, str) else str(data)])

        cmd.append(url)
        return " ".join(shlex.quote(c) for c in cmd)

    @api.model
    def _call_api(self, url, params={}, headers={}, method='GET', type='json'):
        _logger.info('api start')
        log_enable = self._log_api_call and not self._context.get('disable_api_log')
        log_call_stack = self._log_call_stack and not self._context.get('disable_api_log')
        call_stack = ''
        if log_call_stack:
            call_stack = ''
            try:
                frame_infos = inspect.stack()
                for f_idx, f_info in enumerate(frame_infos):
                    call_stack += f'  File "{f_info.filename}", line {f_info.lineno}, in {f_info.function}\n'
            except Exception as e:
                call_stack += 'Lỗi inspector code' + str(e)

        if log_enable:
            request_time = fields.Datetime.now()
            with self.pool.cursor() as cr_create:
                pretty_params = params
                try:
                    if isinstance(pretty_params, str):
                        if type == 'json':
                            pretty_params = json_dump(json.loads(pretty_params))
                        if type == 'xml':
                            pretty_params = pretty_print_xml_minidom(pretty_params)
                except:
                    pass
                if url == 'https://api.bizfly.vn/crm/_api/base-table/update':
                    pretty_params = json.dumps(pretty_params, ensure_ascii=False)
                cr_create.execute(f"""
                                INSERT INTO api_call_log
                                    (create_date, create_uid, user_id, res_id, res_model, api_type, name, url, method, headers, params, call_stack, request_time)
                                VALUES 
                                    (NOW() at time zone 'UTC', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id""", [self.env.user.id, self.env.user.id, self.id if self else None, self._name, self._api_type, self._description or self._name, url, method, json_dump(headers), pretty_params, call_stack, request_time])
                log_result = cr_create.fetchall()
                id = log_result[0][0]
        if type == 'xml':
            params = params.encode('utf-8')

        # retry nếu 404
        for i in range(3):
            if url == 'https://api.bizfly.vn/crm/_api/base-table/update':
                result = requests.post(url, headers=headers, json=params)
            elif url == 'https://api.etelecom.vn/v1/partner.Zalo/SendZNS':
                _logger.error("Params DEBUG SendZNS:\n%s", params)
                if isinstance(params, str):
                    params = json.loads(params)
                result = requests.request(method, url, headers=headers, json=params)
            else:
                result = requests.request(method, url, headers=headers, data=params)
            curl_cmd = self.to_curl(method, url, headers, params)
            _logger.error("CURL DEBUG SendZNS:\n%s", curl_cmd)
            if result.status_code != '404':
                break

            _logger.info('Lỗi 404, retry after 0.5s')
            time.sleep(0.5)

        if log_enable:
            response_time = fields.Datetime.now()
            delta = response_time - request_time
            api_duration = delta.total_seconds()
            with self.pool.cursor() as cr_write:
                response_text = result.text.replace("\x00", "\uFFFD")
                try:
                    if type == 'json':
                        response_text = json_dump(json.loads(result.text))
                    elif type == 'xml':
                        root = etree.fromstring(pretty_print_xml_minidom(result.text))
                        response_text = etree.tostring(root, pretty_print=True, encoding=str)
                except:
                    pass
                cr_write.execute("""UPDATE api_call_log SET response_time = %s, response_status_code = %s,  response_text = %s, api_duration = %s where id = %s""", (response_time, result.status_code, response_text, api_duration, id))
        _logger.info('api end')
        try:
            if type == 'xml':
                return etree.fromstring(result.content)
            elif type == 'file':
                return result.content
            else:
                return result.json()
        except:
            return {'error': result.text}
