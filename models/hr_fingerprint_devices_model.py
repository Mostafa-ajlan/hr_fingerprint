# -*- coding: utf-8 -*-

from odoo.exceptions import UserError, ValidationError
from odoo import models, fields, api, _
from odoo.modules.registry import Registry
from datetime import datetime
import logging
import json
import threading
import base64

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
    _description = _(' Hr Fingerprint Device Management')
    _inherit = ['mail.thread', 'mail.activity.mixin']

    BATCH_SIZE = 1000
    device_threads = {}
    stop_events = {}  # قاموس لتخزين كائنات Event للتحكم في إيقاف الـ threads
    
    # Fields for device information
    name = fields.Char(string=_('Device Display Name'), readonly=True, )
    device_name = fields.Char(string=_('Main Device Name'), readonly=True, )
    serial_number = fields.Char(string=_('Serial Number'), readonly=True, )
    model = fields.Char(string=_('Model'), readonly=True, )
    firmware_version = fields.Char(string=_('Firmware Version'), readonly=True, )
    platform = fields.Char(string=_('Model'), readonly=True, )
    manufacturer = fields.Char(string=_('Manufacturer'), default='ZKTeco', readonly=True, )
    mac_address = fields.Char(string=_('MAC Address'), readonly=True, )

    # Fields for connection type of device
    connection_mode = fields.Selection([
        ('iot', _('IoT Box')),
        ('direct', _('Direct')),
        ('push', _('Push')),
    ], string=_('Connection Mode'), required=True, )

    connection_type = fields.Selection([
        ('network', _('Network')),
        ('serial', _('Serial')),
        ('usb', _('USB')),
    ], string=_('Connection Type'), default="network", readonly=True, )

    # Fields for using IoT device
    # use_iot_box = fields.Boolean(string='Uses IoT Box', readonly=True, help="Check this box if the device is connected through an IoT Box.")
    
    iot_device_id = fields.Many2one(
        'iot.device',
        string=_('IoT Device'),
        domain="[('type', '=', 'biometric')]",
        readonly=True,
    )

    # For Network connection
    ip_address = fields.Char(string=_('IP Address/URLs'), readonly=True, )
    port = fields.Integer(string=_('Port'), default=4370, readonly=True, )
    password = fields.Char(string=_('Device Password'), readonly=True, )
    protocol = fields.Selection([
        ('tcp', 'TCP/IP'),
        ('udp', 'UDP')
    ], string=_('Protocol'), default='tcp', readonly=True, )
    subnet_mask = fields.Char(string=_('Subnet Mask'), readonly=True, )
    gateway = fields.Char(string=_('Gateway'), readonly=True, help="e.g., 192.168.1.1")

    connection_status = fields.Selection([
            ('connected', 'Connected'),
            ('disconnected', 'Disconnected'),
            ('unknown', 'Unknown')
        ], 
        string=_('Connection Status'), 
        compute='_compute_connection_status', 
        store=True, 
        readonly=True, 
    )

    last_connected = fields.Datetime(string=_('Last Connected'), readonly=True)

    # last_synchronized = fields.Datetime(string='Last Synchronized', readonly=True) 

    # Setting Fields
    connection_timeout = fields.Integer(string=_('Connection Timeout (seconds)'), default=30, readonly=True,)

    auto_sync_time = fields.Boolean(string=_('Auto Synchronize Time'))


    verify_method = fields.Selection([
        ('fingerprint', _("Fingerprint Only")),
        ('card', _("Card Only")),
        ('mixed', _("Fingerprint + Card")),
        ('face', _("Face Recognition"))
    ], string=_('Verification Method'), default='fingerprint',readonly=True, )
    active_device = fields.Boolean(string=_('Active'), default=True)

    # Device Setting Fields (Configuration)
    photo_fun_on = fields.Boolean(string=_('Photo Function Enabled'))
    finger_fun_on = fields.Boolean(string=_('Fingerprint Function Enabled'))
    face_fun_on = fields.Boolean(string=_('Face Recognition Enabled'))
    fv_fun_on = fields.Boolean(string=_('FV Function Enabled'))
    pv_fun_on = fields.Boolean(string=_('PV Function Enabled'))
    error_delay = fields.Integer(string=_('Error Delay (seconds)'), default=30)
    trans_interval = fields.Integer(string=_('Transmission Interval (minutes)'), default=10)
    realtime = fields.Boolean(string=_('Realtime Update'), default=True)
    delay = fields.Integer(string=_('Delay (seconds)'), default=10)
    trans_times = fields.Char(string=_('Transmission Times'), default='00:00;14:05')

    # Statistic Fields
    user_count = fields.Integer(string=_('User Count'), default=0,)
    max_user_count = fields.Integer(string=_('Max User Count'), default=0,)

    fp_count = fields.Integer(string=_('Fingerprint Count'), default=0,)
    max_finger_count = fields.Integer(string=_('Max Finger Count'), default=0,)

    face_count = fields.Integer(string=_('Face Count'), default=0,)
    max_face_count = fields.Integer(string=_('Max Face Count'), default=0,)

    fv_count = fields.Integer(string=_('FV Count'), default=0,)
    max_fv_count = fields.Integer(string=_('Max FV Count'), default=0,)
    pv_count = fields.Integer(string=_('PV Count'), default=0,)
    max_pv_count = fields.Integer(string=_('Max PV Count'), default=0,)
    transaction_count = fields.Integer(string=_('Transaction Count'), default=0, readonly=True)
    max_user_photo_count = fields.Integer(string=_('Max User Photo Count'))
    max_att_log_count = fields.Integer(string=_('Max Attendance Log Count'))
    att_log_count = fields.Integer(
        string=_('Attendance Log Count'),
        compute='_compute_att_log_count',
        store=False,
        readonly=True
    )

    user_usage = fields.Char(
        string=_('Users Usage'),
        compute='_compute_user_usage',
        store=False,
        readonly=True
    )
    fp_usage = fields.Char(
        string=_('Fingerprint Usage'),
        compute='_compute_fp_usage',
        store=False,
        readonly=True
    )
    face_usage = fields.Char(
        string=_('Face Usage'),
        compute='_compute_face_usage',
        store=False,
        readonly=True
    )
    fv_usage = fields.Char(
        string=_('FV Usage'),
        compute='_compute_fv_usage',
        store=False,
        readonly=True
    )
    pv_usage = fields.Char(
        string=_('PV Usage'),
        compute='_compute_pv_usage',
        store=False,
        readonly=True
    )

    
    # Relation Fields
    user_ids = fields.One2many('hr.fingerprint.user', 'device_id', string=_('Users'))
    template_ids = fields.One2many('hr.fingerprint.template', 'device_id', string=_('Fingerprints'))
    attendance_ids = fields.One2many('fingerprint.attendance', 'device_id', string=_('Attendance Records'))
    command_ids = fields.One2many(
        'fingerprint.device.command', 
        'device_id', 
        string=_('Device Commands'),
    )
    language = fields.Selection(
        selection=[
            ('69', 'العربية'), 
            ('1', 'English'),
        ],
        string=_('Language')
    )
    push_version = fields.Char(string=_('Push Version'))
    oem_vendor = fields.Char(string=_('OEM Vendor'))
    reg_device_type = fields.Integer(string=_('Registered Device Type'))
    last_communication = fields.Datetime(string=_('Last Communication'), readonly=True)

    # إصدارات الميزات
    fp_version = fields.Char(string=_('Fingerprint Version'))
    face_version = fields.Char(string=_('Face Recognition Version'))
    fv_version = fields.Char(string=_('FV Version'))
    pv_version = fields.Char(string=_('PV Version'))

    # حقول التهيئة
    error_delay = fields.Integer(string=_('Error Delay (seconds)'), default=30)
    last_attlog_stamp = fields.Integer(string=_('Last ATTLOG Stamp'))
    last_operlog_stamp = fields.Integer(string=_('Last OPERLOG Stamp'))
    last_attphoto_stamp = fields.Integer(string=_('Last ATTPHOTO Stamp'))
    trans_flag = fields.Char(string=_('Transmission Flags'), default='AttLog OpLog AttPhoto')

    # Constraints
    _sql_constraints = [
        ('serial_number_unique', 'UNIQUE(serial_number)', _('Serial number must be unique!')),
        ('mac_address_unique', 'UNIQUE(mac_address)', _('Mac address must be unique!')),
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

    @api.depends('connection_mode', 'iot_device_id.connected', 'ip_address', 'port')
    def _compute_connection_status(self):
        for device in self:
            if device.connection_mode == 'iot':
                device.connection_status = 'connected' if device.iot_device_id.connected else 'disconnected'
            elif device.connection_mode == 'direct':
                device.connection_status = self._check_direct_connection(device.ip_address, device.port)
            else:
                device.connection_status = 'unknown'
    
    
    def _check_direct_connection(self, ip_address, port):
        try:
            zk_device = ZK(ip_address, port=port, timeout=5)
            conn = zk_device.connect()
            conn.disconnect()
            return 'connected'
        except Exception:
            return 'disconnected'
    
    
   
    @api.model
    def get_server_datetime(self):
        """
        Return the current server datetime as a string.
        """
        now = fields.Datetime.now()
        return fields.Datetime.to_string(now)
    
    def connect_to_zk_device(self):
        """إنشاء اتصال مع جهاز ZK وإرجاع كائن الاتصال"""
        try:
            zk_device = ZK(
                self.ip_address,
                port=self.port,
                timeout=self.connection_timeout,
                password=int(self.password),
                force_udp=(self.protocol == 'udp'),
            )
            conn = zk_device.connect()
            return zk_device, conn
        except Exception as e:
            _logger.error(
                "Failed to connect to ZK device %s:%s - Error: %s",
                self.ip_address, self.port, str(e)
            )
            return False, False

    def _set_device_time(self, zk_device):
        """ضبط وقت الجهاز ليكون متزامنًا مع وقت السيرفر"""
        try:
            # افترض أن zk_device لديه دالة لضبط الوقت
            zk_device.set_time(datetime.now())
            _logger.info("Device time set successfully.")
        except Exception as e:
            _logger.error("Failed to set device time: %s", e)
    
    def _fetch_device_statistics(self, zk_device):
        """جلب إحصائيات الجهاز"""
        try:
            # قراءة الإحصائيات من الجهاز
            zk_device.read_sizes()
            stats = {
                # إحصائيات المستخدمين
                'user_count': zk_device.users,
                'max_user_count': zk_device.users_cap,

                # إحصائيات البصمات
                'fp_count': zk_device.fingers,
                'max_finger_count': zk_device.fingers_cap,
                
                # إحصائيات الوجوه
                'face_count': zk_device.faces,
                'max_face_count': zk_device.faces_cap,
                
                # إحصائيات السجلات
                'transaction_count': zk_device.records,
                'max_att_log_count': zk_device.rec_cap,
                
                # إحصائيات البطاقات
                # 'cards_count': zk_device.cards,

            }
            return stats
        except Exception as e:
            _logger.error("Error fetching device statistics: %s", str(e))
            return False     
    
    def _fetch_device_info(self, zk_device):
        """جلب معلومات الجهاز"""
        try:
            info = zk_device.get_device_info()
            statistics = self._fetch_device_statistics(zk_device)
            if statistics:
                info.update(statistics)

            print(self.name,"self.namename")
            return {
                'serial_number': info.get('serial_number', ''),
                'name': info.get('device_name', '') if not self.name else self.name,
                'device_name': info.get('device_name', ''),
                'model': info.get('device_name', ''),
                'firmware_version': info.get('firmware_version', ''),
                'platform': info.get('platform', ''),
                'mac_address': info.get('mac_address', ''),
                'user_count': info.get('user_count', 0),
                'fp_count': info.get('fp_count', 0),
                'face_count': info.get('face_count', 0),
                'max_user_count': info.get('max_user_count', 0),
                'max_finger_count': info.get('max_finger_count', 0),
                'max_face_count': info.get('max_face_count', 0),
                'transaction_count': info.get('transaction_count', 0),
                'max_att_log_count': info.get('max_att_log_count', 0),
                'subnet_mask': info.get('subnet_mask', 'Unknown'),
                'gateway': info.get('gateway', 'Unknown'),
            }
        except Exception as e:
            _logger.error("Error fetching device info: %s", str(e))
            return False 

    def _fetch_user_by_user_id(self, user_id):
        """
        Fetches a specific user's data from the device using their user_id.
        :param user_id: The user_id to search for.
        :return: A dictionary of user data if found, False otherwise.
        """
        zk_device, conn = self.connect_to_zk_device()
        if not zk_device or not conn:
            return False
        try:
            users = zk_device.get_users() # Get all users
            for user in users:
                if user.user_id == user_id:
                    return {
                        'device_id': self.id,
                        'user_id': user.user_id,
                        'uid': str(user.uid),
                        'name': user.name,
                        'privilege': str(user.privilege),
                        'password': user.password,
                        'group_id': user.group_id,
                        'card': str(user.card),
                    }
            _logger.warning("User with user_id %s not found on device %s", user_id, self.name)
            return False
        except Exception as e:
            _logger.error("Error fetching user by user_id %s from device %s: %s", user_id, self.name, str(e))
            return False
    
    def _fetch_users(self, zk_device):
        try:
            users = zk_device.get_users()
            user_vals_list = []
            for user in users:
                user_vals_list.append({
                    'device_id': self.id,
                    'user_id': user.user_id,
                    'uid': str(user.uid),
                    'name': user.name,
                    'privilege': str(user.privilege),
                    'password': user.password,
                    'group_id': user.group_id,
                    'card': str(user.card),
                })
            return user_vals_list
        except Exception as e:
            _logger.error("Error fetching users from device: %s", str(e))
            return []
    
    def _fetch_and_create_users(self, zk_device):
        """جلب وإنشاء المستخدمين"""
        try:
            user_vals_list = self._fetch_users(zk_device)
            if user_vals_list:
                # إنشاء المستخدمين على دفعات
                for i in range(0, len(user_vals_list), self.BATCH_SIZE):
                    batch = user_vals_list[i:i + self.BATCH_SIZE]
                    self.env['hr.fingerprint.user'].create(batch)
                return True
            return False
        except Exception as e:
            _logger.error("Error creating users: %s", str(e))
            return False   

    def _fetch_templates(self, zk_device):
        print("_fetch_templates_fetch_templates")
        try:
            templates = zk_device.get_templates()
            template_vals_list = []
            for template in templates:
                user = self.env['hr.fingerprint.user'].search([
                    ('device_id', '=', self.id),
                    ('uid', '=', str(template.uid))
                ], limit=1)
                if user:
                    template_vals_list.append({
                        'device_id': self.id,
                        'user_id': user.id,
                        'fingerprint_id': int(template.fid),
                        'size': int(template.size),
                        'valid': int(template.valid),
                        'template': base64.b64encode(json.dumps(template.json_pack()).encode('utf-8')).decode('utf-8'),
                        'mark': base64.b64encode(template.mark).decode('utf-8')
                    })
            return template_vals_list
        except Exception as e:
            _logger.error("Error fetching templates from device: %s", str(e))
            return []
    
    
    def _fetch_and_create_templates(self, zk_device):
        """جلب وإنشاء القوالب"""
        try:
            template_vals_list = self._fetch_templates(zk_device)
            if template_vals_list:
                for i in range(0, len(template_vals_list), self.BATCH_SIZE):
                    batch = template_vals_list[i:i + self.BATCH_SIZE]
                    self.env['hr.fingerprint.template'].create(batch)
                return True
            return False
        except Exception as e:
            _logger.error("Error creating templates: %s", str(e))
            return False 


    def _fetch_attendance(self, zk_device):
        try:
            attendances = zk_device.get_attendance()
            attendance_vals_list = []
            for att in attendances:
                attendance_vals_list.append({
                    'device_id': self.id,
                    'user_id': att.user_id,
                    'punching_time': att.timestamp,
                    'attendance_type': str(att.status),
                    'punch_type': str(att.punch),
                })
            return attendance_vals_list
        except Exception as e:
            _logger.error("Error fetching attendance from device: %s", str(e))
            return []

    def _fetch_and_create_attendance(self, zk_device):
        """جلب وإنشاء سجلات الحضور والانصراف"""
        try:
            attendance_vals_list = self._fetch_attendance(zk_device)
            if attendance_vals_list:
                # إنشاء سجلات الحضور على دفعات
                for i in range(0, len(attendance_vals_list), self.BATCH_SIZE):
                    batch = attendance_vals_list[i:i + self.BATCH_SIZE]
                    self.env['fingerprint.attendance'].create(batch)
                return True
            return False
        except Exception as e:
            _logger.error("Error creating attendance records: %s", str(e))
            return False           
    
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if record.connection_mode == 'direct' :
                if record.connection_type == 'network' and record.ip_address and record.port:
                    # إنشاء الاتصال
                    zk_device, conn = record.connect_to_zk_device()
                    if not zk_device or not conn:
                        continue

                    try:
                        # ضبط وقت الجهاز
                        record._set_device_time(zk_device)

                        # جلب وحفظ معلومات الجهاز
                        device_info = record._fetch_device_info(zk_device)
                        if device_info:
                            record.write(device_info)

                        fetch_create_users = record._fetch_and_create_users(zk_device)
                        if not fetch_create_users:
                            _logger.error("Error in fetch users from machine")

                        
                        fetch_create_template = record._fetch_and_create_templates(zk_device) 
                        if not fetch_create_template:
                            _logger.error("Error in fetch templates from machine")   

                        
                        fetch_create_attendance = record._fetch_and_create_attendance(zk_device) 
                        if not fetch_create_attendance:
                            _logger.error("Error in fetch attendance from machine")   

                    except Exception as e:
                        pass
                    finally:
                        # إغلاق الاتصال
                        if conn:
                            conn.disconnect()
        return records    
    
    def unlink(self):
        """
        التحقق قبل حذف الجهاز - إذا كان مرتبطًا بمستخدمين، يتم تعطيله بدلاً من حذفه
        ويتم عرض رسالة للمستخدم
        """
        for device in self:
            users_count = self.env['hr.fingerprint.user'].search_count([('device_id', '=', device.id)])
            if users_count > 0:
                device.write({'active_device': False})
                self.env.cr.commit()
                raise UserError(_(
                    "Cannot delete device '%s' because it is linked to %s users. "
                    "The device has been deactivated instead."
                ) % (device.name, users_count))
        return super(HrFingerprintDevice, self).unlink()
    
    @api.model
    def action_type_processing(self, device_id):
        """
        معالجة الإجراءات المختلفة على أجهزة البصمة حسب نوع الاتصال
        
        :param device_id: معرف الجهاز
        :return: قاموس يحتوي على نتيجة العملية
        """
        action_type = self.env.context.get('action_type')
        device = self.browse(device_id)
        
        if not device or not device.exists():
            raise UserError(_("Device not found."))
        
        # تهيئة قاموس النتيجة
        result = {
            'status': 'failed',
            'message': '',
            'action_type': action_type,
            'device_id': device_id,
            'device_name': device.name
        }
        
        # التحقق من نوع الاتصال وتوجيه الطلب للمعالج المناسب
        try:
            if device.connection_mode == 'direct':
                result = self._process_direct_action(device, action_type, result)
            elif device.connection_mode == 'push':
                result = self._process_push_action(device, action_type, result)
            # elif device.connection_mode == 'iot':
            #     result = self._process_iot_action(device, action_type, result)
            else:
                result['message'] = _("Unsupported connection mode: %s") % device.connection_mode
        except Exception as e:
            result['message'] = _("Error processing action: %s") % str(e)
            _logger.exception("Error in action_type_processing for device %s: %s", device.name, e)
        
        return result

    def _process_direct_action(self, device, action_type, result):
        """
        معالجة الإجراءات للأجهزة ذات الاتصال المباشر (direct)
        
        :param device: سجل الجهاز
        :param action_type: نوع الإجراء
        :param result: قاموس النتيجة الأولي
        :return: قاموس النتيجة المحدث
        """
        # الاتصال بالجهاز
        zk_device, conn = device.connect_to_zk_device()
        if not zk_device or not conn:
            result['message'] = _("Could not connect to the device.")
            return result
        
        try:
            # تنفيذ الإجراء المطلوب
            action_handlers = {
                'fetch_user': self._handle_fetch_user,
                'download_template': self._handle_download_template,
                'download_attendance': self._handle_download_attendance,
                'reboot_device': self._handle_reboot_device,
                'shutdown_device': self._handle_shutdown_device,
                'clear_attendance': self._handle_clear_attendance,
                'sync_time': self._handle_set_time,
                'get_device_info': self._handle_get_device_info,
            }
            
            if action_type in action_handlers:
                result = action_handlers[action_type](device, zk_device, conn, result)
            else:
                result['message'] = _("Unknown action type: %s") % action_type
        
        except Exception as e:
            result['message'] = _("Error: %s") % str(e)
            _logger.exception("Error in _process_direct_action for device %s: %s", device.name, e)
        
        finally:
            # إغلاق الاتصال
            if conn:
                try:
                    conn.disconnect()
                except Exception:
                    pass
        
        return result

    def _process_push_action(self, device, action_type, result):
        """
        معالجة الإجراءات للأجهزة ذات الاتصال بنظام الدفع (push)
        
        :param device: سجل الجهاز
        :param action_type: نوع الإجراء
        :param result: قاموس النتيجة الأولي
        :return: قاموس النتيجة المحدث
        """
        try:
            # إنشاء أمر جديد للجهاز
            command_vals = {
                'device_id': device.id,
                'action_type': action_type,
                'status': 'pending',
                'created_by': self.env.user.id,
            }
            
            command = self.env['zk.device.command'].create(command_vals)
            
            # تحديث النتيجة
            result.update({
                'status': 'pending',
                'message': _("Command queued for processing."),
                'command_id': command.id
            })
            
            # إرسال إشعار للجهاز إذا كان متصلاً
            if device.connection_status == 'connected':
                # هنا يمكن إضافة كود لإرسال إشعار للجهاز
                pass
        
        except Exception as e:
            result['message'] = _("Error creating command: %s") % str(e)
            _logger.exception("Error in _process_push_action for device %s: %s", device.name, e)
        
        return result


    def _handle_fetch_user(self, device, zk_device, conn, result):
        """معالج جلب المستخدمين"""
        created = device._fetch_and_create_users(zk_device)
        if created:
            result.update({
                'status': 'success',
                'message': _("Users fetched and saved successfully.")
            })
        else:
            result['message'] = _("No users fetched or error occurred.")
        return result

    def _handle_download_template(self, device, zk_device, conn, result):
        """معالج جلب قوالب البصمات"""
        created = device._fetch_and_create_templates(zk_device)
        if created:
            result.update({
                'status': 'success',
                'message': _("Templates fetched and saved successfully.")
            })
        else:
            result['message'] = _("No templates fetched or error occurred.")
        return result

    def _handle_download_attendance(self, device, zk_device, conn, result):
        """معالج جلب سجلات الحضور"""
        created = device._fetch_and_create_attendance(zk_device)
        if created:
            result.update({
                'status': 'success',
                'message': _("Attendance records fetched and saved successfully.")
            })
        else:
            result['message'] = _("No attendance records fetched or error occurred.")
        return result

    def _handle_reboot_device(self, device, zk_device, conn, result):
        """معالج إعادة تشغيل الجهاز"""
        try:
            conn.restart()
            result.update({
                'status': 'success',
                'message': _("Device rebooted successfully.")
            })
        except Exception as e:
            result['message'] = _("Failed to reboot device: %s") % str(e)
        return result

    def _handle_shutdown_device(self, device, zk_device, conn, result):
        """معالج إيقاف تشغيل الجهاز"""
        try:
            conn.poweroff()
            result.update({
                'status': 'success',
                'message': _("Device shutdown successfully.")
            })
        except Exception as e:
            result['message'] = _("Failed to shutdown device: %s") % str(e)
        return result

    def _handle_clear_attendance(self, device, zk_device, conn, result):
        """معالج مسح سجلات الحضور من الجهاز"""
        try:
            conn.clear_attendance()
            result.update({
                'status': 'success',
                'message': _("Attendance records cleared from device successfully.")
            })
        except Exception as e:
            result['message'] = _("Failed to clear attendance records: %s") % str(e)
        return result

    def _handle_set_time(self, device, zk_device, conn, result):
        """معالج ضبط وقت الجهاز"""
        try:
            conn.set_time(datetime.now())
            result.update({
                'status': 'success',
                'message': _("Device time set successfully.")
            })
        except Exception as e:
            result['message'] = _("Failed to set device time: %s") % str(e)
        return result

    def _handle_get_device_info(self, device, zk_device, conn, result):
        """معالج جلب معلومات الجهاز"""
        try:
            device_info = device._fetch_device_info(zk_device)
            if device_info:
                device.write(device_info)
                result.update({
                    'status': 'success',
                    'message': _("Device information updated successfully."),
                    'device_info': device_info
                })
            else:
                result['message'] = _("Failed to fetch device information.")
        except Exception as e:
            result['message'] = _("Failed to get device info: %s") % str(e)
        return result
        
    def write(self, vals):
        result = super(HrFingerprintDevice, self).write(vals)
        if 'auto_sync_time' in vals and self.connection_mode == 'direct':
            if vals['auto_sync_time']:
                self.start_live_caputre()
            else:
                self.end_live_caputre()   
        return result
    
    def start_live_caputre(self):
        """
        بدء عملية الاستماع المباشر لأحداث الجهاز
        """
        self.ensure_one()
        device_identifier = f"{self.env.cr.dbname}_{self.id}"
        
        # التحقق من عدم وجود thread نشط بالفعل لهذا الجهاز
        if device_identifier in self.device_threads:
            _logger.info("Live capture already running for device: %s", self.name)
            return
        
        # إنشاء كائن Event جديد وإعادة تعيينه (clear)
        stop_event = threading.Event()
        
        # إعداد بيانات الجهاز
        device_data = {
            'id': self.id,
            'ip_address': self.ip_address,
            'port': self.port,
            'connection_timeout': self.connection_timeout,
            'password': self.password,
            'protocol': self.protocol,
            'dbname': self.env.cr.dbname,
            'uid': self.env.uid,
            'context': self.env.context,
            'stop_event': stop_event,
        }

        t = threading.Thread(target=self._live_capture_worker_static, args=(device_data,), daemon=True)
        t.start()
        
        self.device_threads[device_identifier] = t
        self.stop_events[device_identifier] = stop_event
        
        _logger.info("Started live capture for device: %s (ID: %s)", self.name, self.id)
        
        return True

    def end_live_caputre(self):
        """
        إيقاف عملية الاستماع المباشر لأحداث الجهاز
        """
        self.ensure_one()
        device_identifier = f"{self.env.cr.dbname}_{self.id}"
        
        # التحقق من وجود thread نشط لهذا الجهاز
        if device_identifier not in self.device_threads:
            _logger.info("No active live capture for device: %s", self.name)
            return
        
        print(self.stop_events," preprepreeeeee")
        # إرسال إشارة لإيقاف الـ thread باستخدام Event
        if device_identifier in self.stop_events:
            self.stop_events[device_identifier].set()
            self.stop_events.pop(device_identifier) 
            _logger.info("Signaled to stop live capture for device: %s (ID: %s)", self.name, self.id)
        
        print(self.stop_events," afterrrrrrrrrrrr")
        if device_identifier in self.device_threads:
            self.device_threads.pop(device_identifier)

        _logger.info("Stopped live capture for device: %s (ID: %s)", self.name, self.id)
        
        return True

    def _register_hook(self):
        super()._register_hook()
        devices = self.env['hr.fingerprint.device'].sudo().search([
            ('connection_mode', '=', 'direct'), 
            ('auto_sync_time', '=', True)], 
        )

        for device in devices:
            stop_event = threading.Event()
            print(stop_event,"gfgfgfgfg")
            device_data = {
                'id': device.id,
                'ip_address': device.ip_address,
                'port': device.port,
                'connection_timeout': device.connection_timeout,
                'password': device.password,
                'protocol': device.protocol,
                'dbname': self.env.cr.dbname,
                'uid': self.env.uid,
                'context': self.env.context,
                'stop_event': stop_event,
            }
            t = threading.Thread(target=self._live_capture_worker_static, args=(device_data,), daemon=True)
            t.start()
            self.device_threads[f"{self.env.cr.dbname}_{device.id}"] = t
            self.stop_events[f"{self.env.cr.dbname}_{device.id}"] = stop_event

    @staticmethod
    def _live_capture_worker_static(device_data):
        """
        دالة ثابتة تعمل في thread منفصل للاستماع إلى أحداث الجهاز
        تستخدم device_data بدلاً من الوصول المباشر إلى self
        """
        # استخراج البيانات من المعلومات المخزنة
        device_id = device_data['id']
        ip_address = device_data['ip_address']
        port = int(device_data['port'])
        connection_timeout = device_data['connection_timeout']
        password = int(device_data['password'])
        protocol = device_data['protocol']
        dbname = device_data['dbname']
        uid = device_data['uid']
        context = device_data['context']
        stop_event = device_data['stop_event']  # كائن Event للتحكم في إيقاف الـ thread
        try:
            # إنشاء اتصال مع جهاز ZK
            zk_device = ZK(
                ip_address,
                port=port,
                timeout=connection_timeout,
                password=password if password else 0,
                force_udp=(protocol == 'udp'),
            )
            conn = zk_device.connect()
            
            if not conn:
                _logger.warning("Failed to connect to device ID: %s", device_id)
                return
                
            # بدء الاستماع للأحداث
            for attendance in conn.live_capture(new_timeout=10):
                print("received for device: ", attendance)
                # التحقق من إشارة التوقف باستخدام Event
                if stop_event.is_set():
                    print("Stop event received for device:",device_id)
                    _logger.info("Stop event received for device %s, stopping live capture", device_id)
                    break
                if attendance is None:
                    continue

                # إنشاء بيئة جديدة للتعامل مع قاعدة البيانات
                registry_obj = Registry(dbname)
                with registry_obj.cursor() as new_cr:
                    env = api.Environment(new_cr, uid, context)
                    
                    # البحث عن المستخدم
                    user = env['hr.fingerprint.user'].search([
                        ('uid', '=', str(attendance.user_id)),
                        ('device_id', '=', device_id)
                    ], limit=1)
                    
                    # إنشاء سجل حضور جديد
                    env['fingerprint.attendance'].create({
                        'device_id': device_id,
                        'user_id': user.id if user else False,
                        'punch_type': str(attendance.punch),
                        'attendance_type': str(attendance.status),
                        'punching_time': attendance.timestamp,
                        'is_used': False,
                    })
                    new_cr.commit()
                        
        except Exception as e:
            _logger.error("Live capture error for device %s: %s", device_id, str(e))
        finally:
            try:
                conn.disconnect()
            except Exception:
                pass

   
    # push protocol functions
    def process_attendance_data(self, data, stamp):
        """
        processing attendance data from the device
        :param data: the raw data from the device
        :param stamp: the timestamp of the data
        """
        Attendance = self.env['fingerprint.attendance']
        User = self.env['hr.fingerprint.user']
        
        for line in data.split('\n'):
            if not line.strip():
                continue
            try:
                parts = line.strip().split('\t')
                if len(parts) < 4:
                    continue
                # analyze the line
                user_id = parts[0]
                timestamp = parts[1]
                verify_code = parts[2]
                attendance_type = parts[3]
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
                    ('punching_time', '=', datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S"))
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

    def process_operation_log(self, data, stamp):
        """
        Process operation log data from the device.
        """
        # Process each line of the operation log
        for line in data.split('\n'):
            _logger.info(f"RRRRRRRRRRRRRRRRRRRRR: {line}")
            if line.startswith('USERPIC'):
                # user picture data processing
                self.user_pic_data(line)
            elif line.startswith('BIOPHOTO') :
                # user bio photo data processing
                self.user_bio_photo_data(line)
            elif line.startswith('ATTLOG'):
                # attendance data processing
                self.process_attendance_data(line , None)
            elif line.startswith('OPERLOG'):
                # operation log processing
                self.process_operation_log(line, None)
            elif line.startswith('FP'):
                # fingerprint data processing
                self.process_fingerprint_data(line)
            elif line.startswith('USER'):
                # user information processing
                self.create_or_update_user_info(line)
            elif line.startswith('BIODATA'):
                # biometric data processing
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

            # create or update biometric data
            biometric = self.env['hr.fingerprint.user.biometric'].sudo().search([
                ('user_id', '=', user.id),
                ('device_id', '=', self.id),
                ('index', '=', int(index)),
                ('type', '=', int(type_)),
            ], limit=1)
            if not biometric:
                # create a new biometric template
                self.env['hr.fingerprint.user.biometric'].sudo().create({
                    'user_id': user.id,
                    'device_id': self.id,
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
                # update existing biometric template
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
                'user_id': user_data.get('PIN'),
                'name': user_data.get('Name', ''),
                'password': user_data.get('Passwd', ''),
                'card': user_data.get('Card', ''),
                'group_id': user_data.get('Grp', 0),
                # 'timezone': user_data.get('TZ', '0001000000000000'),
                'privilege': user_data.get('Pri', 0),
                # 'verify_mode': user_data.get('Verify' , '6'),
                'start_datetime': convert_timestamp(user_data.get('StartDatetime')),
                'end_datetime': convert_timestamp(user_data.get('EndDatetime')),
                # 'vice_card': user_data.get('ViceCard'),
            })
    
    def process_fingerprint_data(self, response_text):
        """
        Parses a fingerprint response from the device and updates or creates the fingerprint template for a user.
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
                    'device_id': self.id,
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
        Parses a user picture response from the device and updates the user's picture data.
        Example response:
        USERPIC PIN=1 FileName=1.jpg Size=8188 Content=/9j/4AAQSkZJRgABAQAAAQABAAD/...
        """
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

            # save the user image
            user.image = content
            user.image_filename = file_name
            user.image_size = size

        except Exception as e:
            _logger.error(f"Error handling USERPIC response: {e}")
            
    def user_bio_photo_data(self, response_text):
        """ 
        Example response:
        BIOPHOTO PIN=1 FileName=1.jpg Size=8188 Content=/9j/4AAQSkZJRgABAQAAAQABAAD/...
        """
        print(f"BIOPHOTO response: {response_text}")
            
    def get_pending_commands(self):
        """
        Retrieve pending commands for the device and mark them as sent.
        Returns a list of command texts that were sent.
        """
        self.ensure_one()
        
        pending_commands = self.env['fingerprint.device.command'].search([
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
