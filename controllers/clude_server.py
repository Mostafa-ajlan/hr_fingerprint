from odoo import http
from odoo.http import request
import json
import time

class IclockController(http.Controller):

    @http.route('/iclock/cdata', type='http', auth='none', methods=['GET'], csrf=False)
    def handshake(self, **kwargs):
        print("handshakehandshakehandshakehandshake")
        print(kwargs,"FDFDDFFDFDDFFDFDFDFDFDFDFDFDFDFDFDFDFD")
        sn = kwargs.get('SN')
        option = kwargs.get('option')
        
        response = (
            f"GET OPTION FROM: {sn}\r\n"
            f"Stamp=9999\r\n"
            f"OpStamp={int(time.time())}\r\n"
            f"ErrorDelay=60\r\n"
            f"Delay=30\r\n"
            f"ResLogDay=18250\r\n"
            f"ResLogDelCount=10000\r\n"
            f"ResLogCount=50000\r\n"
            f"TransTimes=00:00;14:05\r\n"
            f"TransInterval=1\r\n"
            f"TransFlag=1111000000\r\n"
            f"Realtime=1\r\n"
            f"Encrypt=0"
        )
        return response

    @http.route('/iclock/cdata', type='http', auth='none', methods=['POST'], csrf=False)
    def receive_records(self, **kwargs):
        # print("2222222222222")
        # data = request.jsonrequest
        # print(data , "receive_recordsreceive_recordsreceive_records")
       
        # timestamp = data.get('timestamp')
        # print(timestamp , "timestampreceive_recordsreceive_recordsreceive_records")
        print(kwargs,"FDFDDFFDFDDFFDFDFDFDFDFDFDFDFDFDFDFDFD")
        sn = kwargs.get('SN')
        table = kwargs.get('table')
        print(table,"tabletabletabletabletabletabletabletable")
        options = kwargs.get('options')
        print(options,"optionsoptionsoptionsoptions")
        content = request.httprequest.data.decode('utf-8')
        count = 0
        
        try:
            if table == "OPERLOG":
                # Handle operation log
                lines = [line for line in content.splitlines() if line.strip()]
                return f"OK: {len(lines)}"
            
            return f"OK: {count}"
        
        except Exception as e:
            request.env['zkteco.error.log'].create({
                'error': str(e),
                'data': content,
                'sn': sn
            })
            return f"ERROR: {count}\n"

    @http.route('/iclock/test', type='http', auth='none', methods=['GET'], csrf=False)
    def test(self, **kwargs):
        print("testtesttesttesttesttesttesttesttesttest")
        print(kwargs,"FDFDDFFDFDDFFDFDFDFDFDFDFDFDFDFDFDFDFD")
        content = request.httprequest.data.decode('utf-8')
        return "OK"

    @http.route('/iclock/getrequest', type='http', auth='none', methods=['GET'], csrf=False)
    def get_request(self, **kwargs):
        print("get_requestget_requestget_requestget_request")
        print(kwargs,"FDFDDFFDFDDFFDFDFDFDFDFDFDFDFDFDFDFDFD")
        return "OK"