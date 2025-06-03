# -*- coding: utf-8 -*-

from odoo.exceptions import UserError, ValidationError
from odoo import models, fields, api, _
from datetime import datetime
import logging
import socket
import json
import time

_logger = logging.getLogger(__name__)
try:
    from zk import ZK, const
except ImportError:
    _logger.error("Please install pyzk library: pip install pyzk")
    
def convert_timestamp(ts):
    """ Convert timestamp to UTC datetime or return False if invalid."""
    if isinstance(ts, str):
        ts = ts.strip()
        if ts.isdigit():
            ts = int(ts)
    elif isinstance(ts, (int, float)):
        ts = int(ts)
    return datetime.utcfromtimestamp(int(ts)) if ts and ts != '0' else False 

class HrFingerprintDevice(models.Model):
    _name = 'hr.fingerprint.device'
    _description = ' Hr Fingerprint Device Management'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    # Fields for device information
    name = fields.Char(string='Device Display Name', readonly=True, tracking=True)
    serial_number = fields.Char(string='Serial Number', readonly=True, tracking=True)
    model = fields.Char(string='Model', readonly=True, tracking=True)
    firmware_version = fields.Char(string='Firmware Version', readonly=True, tracking=True)
    platform = fields.Char(string='Model', readonly=True, tracking=True)
    manufacturer = fields.Char(string='Manufacturer', default='ZKTeco', readonly=True, tracking=True)
    mac_address = fields.Char(string='MAC Address', readonly=True, tracking=True)

    # Fields for connection type of device
    connection_mode = fields.Selection([
        ('iot', 'IoT Box'),
        ('direct', 'Direct'),
        ('push', 'Push'),
    ], string='Connection Mode', required=True, tracking=True)

    connection_type = fields.Selection([
        ('network', 'Network'),
        ('serial', 'Serial'),
        ('usb', 'USB'),
    ], string='Connection Type', readonly=True, tracking=True)

    # Fields for using IoT device
    # use_iot_box = fields.Boolean(string='Uses IoT Box', readonly=True, help="Check this box if the device is connected through an IoT Box.")
    
    iot_device_id = fields.Many2one(
        'iot.device', 
        string='IoT Device',
        domain="[('type', '=', 'biometric')]",
        readonly=True,
        tracking=True
    )

    # For Network connection
    ip_address = fields.Char(string='IP Address/URLs', readonly=True, tracking=True)
    port = fields.Integer(string='Port', default=4370, readonly=True, tracking=True)
    password = fields.Char(string='Device Password', readonly=True, tracking=True)
    quick_connect = fields.Boolean(string='Quick Connect', readonly=True, help="Recommended for Port Forwarding")
    protocol = fields.Selection([
        ('tcp', 'TCP/IP'),
        ('udp', 'UDP')
    ], string='Protocol', default='tcp', readonly=True, tracking=True)
    subnet_mask = fields.Char(string='Subnet Mask', readonly=True, tracking=True)
    gateway = fields.Char(string='Gateway', readonly=True, help="e.g., 192.168.1.1")
    
    connection_status = fields.Selection([
            ('connected', 'Connected'),
            ('disconnected', 'Disconnected'),
            ('unknown', 'Unknown')
        ], 
        string='Connection Status', 
        compute='_compute_connection_status', 
        store=True, 
        readonly=True, 
        tracking=True
    )

    last_connected = fields.Datetime(string='Last Connected', readonly=True)

    # last_synchronized = fields.Datetime(string='Last Synchronized', readonly=True) 

    # Setting Fields
    connection_timeout = fields.Integer(string='Connection Timeout (seconds)', default=30, readonly=True, tracking=True)

    auto_sync_time = fields.Boolean(string='Auto Synchronize Time')

    sync_interval = fields.Selection([
        ('15', 'Every 15 minutes'),
        ('30', 'Every 30 minutes'),
        ('60', 'Every hour'),
        ('120', 'Every 2 hours'),
        ('360', 'Every 6 hours'),
        ('720', 'Every 12 hours'),
        ('1440', 'Every day'),
    ], string='Sync Interval', default='60')    

    verify_method = fields.Selection([
        ('fingerprint', 'Fingerprint Only'),
        ('card', 'Card Only'),
        ('mixed', 'Fingerprint + Card'),
        ('face', 'Face Recognition')
    ], string='Verification Method', default='fingerprint',readonly=True, tracking=True)
    active = fields.Boolean(string='Active', default=True, readonly=True, tracking=True)

    # Device Setting Fields (Configuration)
    photo_fun_on = fields.Boolean(string='Photo Function Enabled')
    finger_fun_on = fields.Boolean(string='Fingerprint Function Enabled')
    face_fun_on = fields.Boolean(string='Face Recognition Enabled')
    fv_fun_on = fields.Boolean(string='FV Function Enabled')
    pv_fun_on = fields.Boolean(string='PV Function Enabled')
    error_delay = fields.Integer('Error Delay (seconds)', default=30)
    trans_interval = fields.Integer('Transmission Interval (minutes)', default=10)
    realtime = fields.Boolean('Realtime Update', default=True)
    delay = fields.Integer('Delay (seconds)', default=10)
    trans_times = fields.Char('Transmission Times', default='00:00;14:05')

    # Statistic Fields
    user_count = fields.Integer(string='User Count', default=0,)
    max_user_count = fields.Integer(string='Max User Count', default=0,)

    fp_count = fields.Integer(string='Fingerprint Count', default=0,)
    max_finger_count = fields.Integer(string='Max Finger Count', default=0,)

    face_count = fields.Integer(string='Face Count', default=0,)
    max_face_count = fields.Integer(string='Max Face Count', default=0,)

    fv_count = fields.Integer(string='FV Count', default=0,)
    max_fv_count = fields.Integer(string='Max FV Count', default=0,)
    pv_count = fields.Integer(string='PV Count', default=0,)
    max_pv_count = fields.Integer(string='Max PV Count', default=0,)
    transaction_count = fields.Integer(string='Transaction Count', default=0,)
    max_user_photo_count = fields.Integer(string='Max User Photo Count')
    max_att_log_count = fields.Integer(string='Max Attendance Log Count')
    att_log_count = fields.Integer(
        string='Attendance Log Count',
        compute='_compute_att_log_count',
        store=False,
        readonly=True
    )

    user_usage = fields.Char(
        string='Users Usage',
        compute='_compute_user_usage',
        store=False,
        readonly=True
    )
    fp_usage = fields.Char(
        string='Fingerprint Usage',
        compute='_compute_fp_usage',
        store=False,
        readonly=True
    )
    face_usage = fields.Char(
        string='Face Usage',
        compute='_compute_face_usage',
        store=False,
        readonly=True
    )
    fv_usage = fields.Char(
        string='FV Usage',
        compute='_compute_fv_usage',
        store=False,
        readonly=True
    )
    pv_usage = fields.Char(
        string='PV Usage',
        compute='_compute_pv_usage',
        store=False,
        readonly=True
    )

    
    # Relation Fields
    user_ids = fields.One2many('hr.fingerprint.user', 'device_id', string='Users')
    template_ids = fields.One2many('hr.fingerprint.template', 'device_id', string='Fingerprints')
    attendance_ids = fields.One2many('fingerprint.attendance', 'device_id', string='Attendance Records')
    command_ids = fields.One2many(
        'zk.device.command', 
        'device_id', 
        string='Device Commands',
    )
    language = fields.Selection(
        selection=[
            ('69', 'العربية'), 
            ('1', 'English'),
        ],
        string='Language'
    )
    push_version = fields.Char(string='Push Version')
    oem_vendor = fields.Char(string='OEM Vendor')
    reg_device_type = fields.Integer(string='Registered Device Type')
    last_communication = fields.Datetime(string='Last Communication', readonly=True)

    # إصدارات الميزات
    fp_version = fields.Char(string='Fingerprint Version')
    face_version = fields.Char(string='Face Recognition Version')
    fv_version = fields.Char(string='FV Version')
    pv_version = fields.Char(string='PV Version')

    # حقول التهيئة
    error_delay = fields.Integer('Error Delay (seconds)', default=30)
    last_attlog_stamp = fields.Integer('Last ATTLOG Stamp')
    last_operlog_stamp = fields.Integer('Last OPERLOG Stamp')
    last_attphoto_stamp = fields.Integer('Last ATTPHOTO Stamp')
    trans_flag = fields.Char('Transmission Flags', default='AttLog OpLog AttPhoto')
    
    # Constraints 
    _sql_constraints = [
        ('serial_number_unique', 'UNIQUE(serial_number)', 'Serial number must be unique!'),
        # ('ip_port_unique', 'UNIQUE(ip_address, port)', 'IP and Port combination must be unique!'),
    ]

    @api.depends('user_count', 'max_user_count')
    def _compute_user_usage(self):
        for rec in self:
            rec.user_usage = "%s/%s" % (
                rec.user_count or 0,
                rec.max_user_count or 0
            )
    
    @api.depends('fp_count', 'max_finger_count')
    def _compute_fp_usage(self):
        for rec in self:
            rec.fp_usage = "%s/%s" % (
                rec.fp_count or 0,
                rec.max_finger_count or 0
            )
    
    @api.depends('face_count', 'max_face_count')
    def _compute_face_usage(self):
        for rec in self:
            rec.face_usage = "%s/%s" % (
                rec.face_count or 0,
                rec.max_face_count or 0
            )
    
    @api.depends('fv_count', 'max_fv_count')
    def _compute_fv_usage(self):
        for rec in self:
            rec.fv_usage = "%s/%s" % (
                rec.fv_count or 0,
                rec.max_fv_count or 0
            )
    
    @api.depends('pv_count', 'max_pv_count')
    def _compute_pv_usage(self):
        for rec in self:
            rec.pv_usage = "%s/%s" % (
                rec.pv_count or 0,
                rec.max_pv_count or 0
            )

    @api.depends('attendance_ids')
    def _compute_att_log_count(self):
        for rec in self:
            rec.att_log_count = len(rec.attendance_ids)

    @api.onchange('connection_mode')
    def _onchange_connection_mode(self):
        if self.connection_mode == 'iot':
            self.connection_type = False
        elif self.connection_mode == 'direct':
            pass  # يجب على المستخدم اختيار نوع الاتصال
        elif self.connection_mode == 'push':
            self.connection_type = False

    @api.depends('connection_mode', 'iot_device_id.connected', 'ip_address', 'port')
    def _compute_connection_status(self):
        for device in self:
            if device.connection_mode == 'iot':
                device.connection_status = 'connected' if device.iot_device_id.connected else 'disconnected'
            elif device.connection_mode == 'direct':
                device.connection_status = self._check_direct_connection(device.ip_address, device.port)
            else:
                device.connection_status = 'unknown'
    
    def zk_connect(self):
        """الاتصال بالجهاز عبر pyzk وإرجاع كائن الاتصال"""
        self.ensure_one()
        if not self.ip_address or not self.port:
            raise UserError(_("IP address and port are required for device connection."))
        try:
            zk_device = ZK(self.ip_address, port=self.port, timeout=10)
            conn = zk_device.connect()
            return zk_device, conn
        except Exception as e:
            raise UserError(_("Failed to connect to device: %s") % str(e))
        
    def zk_get_device_info(self, zk_device):
        """جلب معلومات الجهاز"""
        try:
            info = zk_device.get_device_info()
            return {
                'serial_number': info.get('serialnumber', ''),
                'model': info.get('device_name', ''),
                'firmware_version': info.get('firmware_version', ''),
                'platform': info.get('platform', ''),
            }
        except Exception as e:
            raise UserError(_("Failed to get device info: %s") % str(e))    
        
    def zk_get_users(self, zk_device):
        """جلب المستخدمين من الجهاز"""
        try:
            return zk_device.get_users()
        except Exception as e:
            raise UserError(_("Failed to get users: %s") % str(e))   

    def zk_get_templates(self, zk_device):
        """جلب القوالب من الجهاز"""
        try:
            return zk_device.get_templates()
        except Exception as e:
            raise UserError(_("Failed to get templates: %s") % str(e))   

    def zk_get_attendance(self, zk_device):
        """جلب الحضور والانصراف من الجهاز"""
        try:
            return zk_device.get_attendance()
        except Exception as e:
            raise UserError(_("Failed to get attendance: %s") % str(e))      
    
    def _check_direct_connection(self, ip_address, port):
        try:
            zk_device = ZK(ip_address, port=port, timeout=5)
            conn = zk_device.connect()
            conn.disconnect()
            return 'connected'
        except Exception:
            return 'disconnected'
    
    def action_test_connection(self):
        """Test connection to the device"""
        self.ensure_one()
        if self.connection_mode == 'iot':
            if self.iot_device_id:
                if self.iot_device_id.connected:
                    message = _("IoT Box %s is connected!") % self.iot_device_id.name
                    self._message_log(body=message)
                    title = _('Success')
                    message_type = 'success'
                    
                else:
                    message = _("IoT Box %s is not connected!") % self.iot_device_id.name
                    title = _('Warning')
                    message_type = 'warning'
                    self._message_log(body=message)

                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': title,
                        'message': message,
                        'type': message_type,
                        'sticky': False,
                    }
                }
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Warning'),
                        'message': _("Please select an IoT device for this connection type."),
                        'type': 'warning',
                        'sticky': False,
                    }
                }
            
        # try:
        #     zk_device, conn = self._connect_with_retry()
        #     conn.disconnect()
            
        #     message = _("Connection to device %s successful!") % self.name
        #     self._message_log(body=message)
            
        #     return {
        #         'type': 'ir.actions.client',
        #         'tag': 'display_notification',
        #         'params': {
        #             'title': _('Success'),
        #             'message': message,
        #             'type': 'success',
        #             'sticky': False,
        #         }
        #     }
        # except Exception as e:
        #     error_msg = _("Connection failed for device %s: %s") % (self.name, str(e))
        #     _logger.error(error_msg)
        #     raise UserError(error_msg)
    
    def action_download_attendance(self):
        """Download attendance records from device"""
        self.ensure_one()
        if self.connection_mode == 'iot':
            if self.iot_device_id:
                if self.iot_device_id.connected:
                    self.send_to_iot_box(self.iot_device_id ,)
                    # Implement IoT device sync logic here
                    pass
                else:
                    raise UserError(_("IoT Box %s is not connected!") % self.iot_device_id.name)
        else:
            raise UserError(_("Please select an IoT device for this connection type."))

        # if self.connection_type != 'direct':
        #     raise UserError(_("This action is only available for direct connection devices"))
        
        # try:
        #     zk_device, conn = self._connect_with_retry()
            
        #     # Get attendance records
        #     attendances = zk_device.get_attendance()
        #     _logger.info("Found %s attendance records in device %s", len(attendances), self.name)
            
        #     # Process attendance records
        #     created_count = 0
        #     for att in attendances:
        #         # Implement your attendance processing logic here
        #         # Example: Create hr.attendance records
        #         pass
                
        #     conn.disconnect()
            
        #     self.last_attendance_download = fields.Datetime.now()
            
        #     message = _("Downloaded %s attendance records from %s") % (created_count, self.name)
        #     self._message_log(body=message)
            
        #     return {
        #         'type': 'ir.actions.client',
        #         'tag': 'display_notification',
        #         'params': {
        #             'title': _('Success'),
        #             'message': message,
        #             'type': 'success',
        #             'sticky': False,
        #         }
        #     }
            
        # except Exception as e:
        #     error_msg = _("Failed to download attendance from %s: %s") % (self.name, str(e))
        #     _logger.error(error_msg)
        #     raise UserError(error_msg)
    
    def send_to_iot_box(self, device, websocket=True):
        """
            Send the dictionary in message to the iot_box via websocket, or return the data to be sent by longpolling.
        """
        iot_identifiers = device['iot_id']
        print(iot_identifiers,"iot_identifiersiot_identifiersiot_identifiers")
        self._send_websocket({
            "iotDevice":{
                "iotIdentifiers": device['iot_id'].identifier,
                "identifier": device['identifier'],
                "id": device['id']
            }
        })
        pass
        # if not websocket:
        #     return [
        #         [
        #             self.env["iot.box"].search([("identifier", "=", device["iotIdentifier"])]).ip,
        #             device["identifier"],
        #             device['name'],
        #             data_base64,
        #         ]
        #         for device in devices
        #     ]

        # self._send_websocket({
        #     "iotDevice": {
        #         "iotIdentifiers": list(iot_identifiers),
        #         "identifiers": [{
        #             "identifier": device["identifier"],
        #             "id": device["id"]
        #         } for device in devices],
        #     },
        #     "print_id": print_id,
        #     "document": data_base64
        # })
        # return print_id
    
    def _send_websocket(self, message):
        """
            Send the dictionnary in message to the iot_box via websocket and return True.
        """
        print(message,"messagemessagemessagemessage",self.env['iot.channel'].get_iot_channel())
        self.env['bus.bus']._sendone(self.env['iot.channel'].get_iot_channel(), 'iot_action', message)
        return True
   
    # @api.model_create_multi
    # def create(self, vals_list):
    #     for vals in vals_list:
    #         device = super(HrFingerprintDevice, self).create(vals)
    #         if device.connection_mode == 'direct' and device.ip_address:
    #             # جلب بيانات الجهاز عند الإنشاء
    #             device._fetch_device_info_on_create()
    
    # @api.model_create_multi
    # def create(self, vals_list):
    #     records = super().create(vals_list)
    #     for rec in records:
    #         rec._fetch_device_info_on_create()
    #     return records
    
    # def write(self, vals):
    #     res = super().write(vals)
    #     for rec in self:
    #         if 'iot_device_id' in vals or 'ip_address' in vals or 'serial_number' in vals:
    #             rec._fetch_device_info_on_create()
    #     return res
    
    def _fetch_device_info_on_create(self):
        if self.connection_mode == 'iot' and self.iot_device_id:
            # جلب بيانات الجهاز من IoT
            data = self.env['iot.device'].get_iot_box_data([self.iot_device_id.id], self.name)
            if data:
                self.write({
                    'serial_number': data.get('serial_number', ''),
                    'model': data.get('model', ''),
                    'firmware_version': data.get('firmware_version', ''),
                    'platform': data.get('platform', ''),
                })
        elif self.connection_mode == 'direct' and self.ip_address:
            # جلب بيانات الجهاز عبر الشبكة
            try:
                zk_device = ZK(self.ip_address, port=self.port, timeout=5)
                conn = zk_device.connect()
                info = zk_device.get_device_info()
                self.write({
                    'serial_number': info.get('serialnumber', ''),
                    'model': info.get('device_name', ''),
                    'firmware_version': info.get('firmware_version', ''),
                    'platform': info.get('platform', ''),
                })
                conn.disconnect()
            except Exception as e:
                raise UserError(_("Failed to connect to device: %s") % str(e))

    # def unlink(self):
    #     for device in self:
    #         if device.user_ids:
    #             device.write({'active': False})
    #             device.user_ids.write({'active': False})
    #             raise UserError(_("Cannot delete device with linked users. Device and users have been deactivated instead."))
    #     return super().unlink()

    # def action_download_attendance(self):
    #     self.ensure_one()
    #     if not self.active:
    #         raise UserError(_("Device is inactive. Operation not allowed."))        


    # push protocol functions 
    def process_attendance_data(self, data, stamp):
        """
        processing attendance data from the device
        :param data: the raw data from the device
        :param stamp: the timestamp of the data
        """
        _logger.info(f"Processing attendance data for device {self.serial_number}")

        Attendance = self.env['fingerprint.attendance']
        User = self.env['hr.fingerprint.user']
        
        for line in data.split('\n'):
            if not line.strip():
                continue
            try:
                parts = line.strip().split('\t')
                if len(parts) < 4:
                    continue
                print(line,"line")  
                print(parts,"parts")  
                # analyze the line
                user_id = parts[0]
                timestamp = parts[1]
                verify_code = parts[2]
                attendance_type = parts[3]
                print(f"user_id: {user_id}, timestamp: {timestamp}, verify_code: {verify_code}, attendance_type: {attendance_type}")

                # check if user_id is a valid integer
                valid_codes = dict(self.env['fingerprint.attendance']._fields['punch_type'].selection).keys()
                punch_type = verify_code if verify_code in valid_codes else '255'

                # search for the user by device_id and user_id
                user = User.sudo().search([
                    ('device_id', '=', self.id),
                    ('user_id', '=', user_id)
                ], limit=1)
                if not user:
                    user = User.sudo().create({
                        'device_id': self.id,
                        'user_id': user_id ,
                        'name': f"مستخدم {user_id}",    
                        'privilege': '0' # default privilege
                    })
                    _logger.info(f"Created new user: {user.name} (ID: {user_id})")
                    
                # check if the user already exists in the attendance log
                already_exists = Attendance.sudo().search_count([
                    ('user_id', '=', user.id),
                    ('timestamp', '=', datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S"))
                ])
                if already_exists:
                    continue  # skip if the attendance record already exists
                # create a new attendance record
                Attendance.sudo().create({
                    'device_id': self.id,
                    'user_id': user.id,
                    'punching_time': datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S"),
                    'punch_type': punch_type,
                    'attendance_type': attendance_type
                })
                
            except Exception as e:
                _logger.error(f"Error processing line: {line}\nError: {str(e)}")
                continue
        
        # update the last attendance log stamp
        if stamp and stamp.isdigit():
            self.write({'last_attlog_stamp': int(stamp)})
        _logger.info(f"Processed attendance records for device {self.serial_number}")

    def process_operation_log(self, data, stamp):
        """
        Process operation log data from the device.
        """
        for line in data.split('\n'):
            if line.startswith('USERPIC'):
                self.user_pic_data(line)
            elif line.startswith('FP'):
                self.process_fingerprint_data(line)
            elif line.startswith('USER'):
                self.create_or_update_user_info(line)
            elif line.startswith('BIODATA'):
                self.process_biometric_file(line)
            else:
                _logger.info(f"Unknown operation log line: {line}")
        if stamp and stamp.isdigit():
            self.write({'last_operlog_stamp': int(stamp)})
        _logger.info(f"Processed operation logs successfully")

    def process_biometric_file(self, file_content):
        """
        file_content: a string containing multiple lines of BIODATA entries.
        """
        lines = file_content.strip().split('\n')
        for line in lines:
            try:
                self.user_biometric_data(line)
            except Exception as e:
                _logger.error({'line': line, 'status': 'error', 'error': str(e)})
                continue
            
    def user_biometric_data(self, data_line):
        """
        extract data from a BIODATA line:
        BIODATA Pin=1 No=0 Index=14 Valid=1 Duress=0 Type=2 MajorVer=12 MinorVer=0 Format=0 Tmp=apUBEOwDxqMCAA...
        """
        import re
        try:
            # extract fields from the text
            if data_line.startswith("BIODATA"):
                data_line = data_line[len("BIODATA "):]
            regex = r"Pin=(\d+)\s+No=(\d+)\s+Index=(\d+)\s+Valid=(\d+)\s+Duress=(\d+)\s+Type=(\d+)\s+MajorVer=(\d+)\s+MinorVer=(\d+)\s+Format=(\d+)\s+Tmp=(.+)"
            match = re.match(regex, data_line.strip())
            if not match:
                raise ValueError("Error parsing BIODATA line: %s" % data_line)

            # extract matched groups
            user_id, no, index, valid, duress, type_, major_ver, minor_ver, format_, tmp = match.groups()
            user = self.env['hr.fingerprint.user'].sudo().search([('user_id', '=', user_id)], limit=1)
            if not user:
                raise ValueError(f"No biometric user found with ID {user_id}")

            biometric = self.env['hr.fingerprint.user.biometric'].sudo().search([
                ('user_id', '=', user.id),
                ('index', '=', int(index)),
                ('type', '=', int(type_)),
            ], limit=1)
            if not biometric:
                # create a new biometric template
                self.env['hr.fingerprint.user.biometric'].sudo().create({
                    'user_id': user.id,
                    'no': int(no),
                    'index': int(index),
                    'valid': bool(int(valid)),
                    'duress': bool(int(duress)),
                    'type': int(type_),
                    'major_ver': int(major_ver),
                    'minor_ver': int(minor_ver),
                    'format': int(format_),
                    'template': tmp.strip(),
                })
            else:
                biometric.write({
                    'no': int(no),
                    'valid': bool(int(valid)),
                    'duress': bool(int(duress)),
                    'major_ver': int(major_ver),
                    'minor_ver': int(minor_ver),
                    'format': int(format_),
                    'template': tmp.strip(),
                })
                
        except Exception as e:
            _logger.error(f"Error handling BIODATA response: {e}")

    def create_or_update_user_info(self, line):
        """
        create or update user information from a USER line.
        Example line:
        USER PIN=1 Name=John Doe Passwd=1234 Card=12345678 Grp=1 TZ=0001000000000000 Pri=0 Verify=6 StartDatetime=1700000000 EndDatetime=1709999999 ViceCard=Vice123
        """
        user_data = {}
        parts = line[5:].strip().split('\t')  # تجاهل كلمة USER في البداية
        for part in parts:
            if '=' in part:
                key, value = part.split('=', 1)
                user_data[key.strip()] = value.strip()
                
        user = self.env['hr.fingerprint.user'].sudo().search([
            ('device_id', '=', self.id),
            ('user_id', '=', user_data.get('PIN'))
        ], limit=1)
        
        if user:
            user.write({
                'name': user_data.get('Name', user.name),
                'password': user_data.get('Passwd', user.password),
                'card': user_data.get('Card', user.card),
                'group_id': user_data.get('Grp', user.group_id),
                # 'timezone': user_data.get('TZ', user.timezone),
                'privilege': user_data.get('Pri', user.privilege),
                # 'verify_mode': user_data.get('Verify', user.verify_mode),
                'start_datetime': convert_timestamp(user_data.get('StartDatetime')) if user_data.get('StartDatetime') else user.start_datetime,
                'end_datetime': convert_timestamp(user_data.get('EndDatetime')) if user_data.get('EndDatetime') else user.end_datetime,
                # 'vice_card': user_data.get('ViceCard', user.vice_card),
            })
        else:
            self.env['hr.fingerprint.user'].create({
                'device_id': self.id,
                'user_id': user_data['PIN'],
                'name': user_data.get('Name', ''),
                'password': user_data.get('Passwd', ''),
                'card_number': user_data.get('Card', ''),
                'group': user_data.get('Grp', 0),
                'timezone': user_data.get('TZ', '0001000000000000'),
                'privilege': user_data.get('Pri', 0),
                'verify_mode': user_data.get('Verify' , '6'),
                'start_datetime': convert_timestamp(user_data.get('StartDatetime')),
                'end_datetime': convert_timestamp(user_data.get('EndDatetime')),
                'vice_card': user_data.get('ViceCard'),
            })
            
    def process_fingerprint_data(self, response_text):
        """
        Example line:
        FP PIN=1 FID=6 Size=496 Valid=1 TMP=...

        Parses and stores fingerprint for a biometric user.
        """
        try:
            parts = response_text.strip().split()
            user_id = None
            fid = None
            size = None
            valid = None
            tmp = None

            for part in parts:
                if part.startswith("PIN="):
                    user_id = part.split("=")[1]
                elif part.startswith("FID="):
                    fid = int(part.split("=")[1])
                elif part.startswith("Size="):
                    size = int(part.split("=")[1])
                elif part.startswith("Valid="):
                    valid = part.split("=")[1] == '1'
                elif part.startswith("TMP="):
                    tmp = response_text.split("TMP=")[1]  # كل ما بعد TMP=

            if not (user_id and fid is not None and tmp):
                raise ValueError("Incomplete FP data")

            # check if the user exists
            user = self.env['hr.fingerprint.user'].search([('user_id', '=', user_id)], limit=1)
            if not user:
                raise ValueError(f"No biometric user found with ID {user_id}")

            fingerprint = self.env['hr.fingerprint.template'].sudo().search([
                ('user_id', '=', user.id ),
                ('fingerprint_id', '=', fid)
            ], limit=1)
            # create or update the fingerprint template
            if not fingerprint:
                self.env['hr.fingerprint.template'].sudo().create({
                    'user_id': user.id,
                    'fingerprint_id': fid,
                    'template': tmp,
                    'valid': valid,
                    'size': size,
                })
            else:
                fingerprint.write({
                    'template': tmp,
                    'valid': valid,
                    'size': size,
                })

        except Exception as e:
            _logger.error(f"Error handling FP response: {e}")
            
    def user_pic_data(self, response_text):
        """
        Example response:
        USERPIC PIN=1 FileName=1.jpg Size=8188 Content=/9j/4AAQSkZJRgABAQAAAQABAAD/...
        """
        import base64
        try:
            # parse the response text
            parts = response_text.strip().split()
            user_id = None
            file_name = None
            size = None
            content = None

            for part in parts:
                if part.startswith("PIN="):
                    user_id = part.split("=")[1]
                elif part.startswith("FileName="):
                    file_name = part.split("=")[1]
                elif part.startswith("Size="):
                    size = int(part.split("=")[1])
                elif part.startswith("Content="):
                    content = response_text.split("Content=")[1]  # كل ما بعد Content=

            if not (user_id and content):
                raise ValueError("Incomplete USERPIC data")

            # check if the user exists
            user = self.env['hr.fingerprint.user'].sudo().search([('user_id', '=', user_id)], limit=1)
            if not user:
                raise ValueError(f"No biometric user found with ID {user_id}")

            # convert the base64 content to bytes
            image_bytes = base64.b64decode(content) if content else b''

            # save the user image
            user.image = content
            user.image_filename = file_name
            user.image_size = size
            user.photo = base64.b64encode(image_bytes)

        except Exception as e:
            _logger.error(f"Error handling USERPIC response: {e}")
            
    def get_pending_commands(self):
        """
        Retrieve pending commands for the device and mark them as sent.
        Returns a list of command texts that were sent.
        """
        self.ensure_one()
        
        pending_commands = self.env['zk.device.command'].search([
            ('device_id', '=', self.id),
        ], order='create_date',limit=1)
        
        command_texts = []
        if pending_commands:
            command_texts.append(pending_commands.command_data)
            pending_commands.write({'state': 'sent', 'send_date': fields.Datetime.now()})
        return command_texts
    
    def update_communication_time(self):
        """
        Update the last communication time and status of the device.
        """
        self.ensure_one()
        # old_status = self.status
        new_vals = {
            'last_communication': fields.Datetime.now(),
            # 'status': 'online'
        }
        # if old_status != 'online':
            # new_vals['status'] = 'online'
            # self.message_post(body="Device came online")
        self.write(new_vals)