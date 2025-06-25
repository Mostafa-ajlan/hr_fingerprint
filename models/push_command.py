from odoo import models, fields, api
import logging
import json


_logger = logging.getLogger(__name__)

class ZKDeviceCommand(models.Model):
    _name = 'fingerprint.device.command'
    _description = 'Fingerprint Device Command'
    _order = 'create_date desc'
    
    device_id = fields.Many2one('hr.fingerprint.device', 'Device', required=True)
    command_id = fields.Char('Command ID', required=True)
    command_type = fields.Selection([
        ('update_user', 'تحديث مستخدم'),
        ('delete_user', 'حذف مستخدم'),
        ('update_fingerprint', 'تحديث بصمة'),
        ('update_face', 'تحديث وجه'),
        ('update_userpic', 'تحديث صورة مستخدم'),
        ('send_sms', 'إرسال رسالة'),
        ('query_attlog', 'استعلام سجلات الحضور'),
        ('query_userinfo', 'استعلام معلومات مستخدم'),
        ('reboot_device', 'اعادة تشغيل الجهاز'),
        ('query_all_users', 'جلب كل المستخدمين')
    ], string='نوع الأمر', required=True)
    command_data = fields.Text(string='بيانات الأمر',compute="_compute_command_data" , store=True)
    state = fields.Selection([
        ('draft', 'مسودة'),
        ('pending', 'معلق'),
        ('sent', 'تم الإرسال'),
        ('done', 'مكتمل'),
        ('failed', 'فشل')
    ], string='الحالة', default='draft')
    return_code = fields.Char('Return Code')
    create_date = fields.Datetime('Creation Date', default=fields.Datetime.now)
    send_date = fields.Datetime('Send Date')
    execution_date = fields.Datetime('Execution Date')
    response_data = fields.Text('Response Data')
    
    def name_get(self):
        result = []
        for record in self:
            name = f"{record.command_id} - {record.command_type} ({record.state})"
            result.append((record.id, name))
        return result
    
    def mark_as_failed(self):
        """Mark command as failed"""
        self.write({'state': 'failed'})
    
    def resend_command(self):
        """Resend failed command"""
        if self.state == 'failed':
            self.write({'state': 'pending'})
            
    def parse_command(self):
        """تحليل نص الأمر إلى أجزائه"""
        cmd_parts = self.command_text.split(':')
        return {
            'prefix': cmd_parts[0],
            'cmd_id': cmd_parts[1],
            'command': ':'.join(cmd_parts[2:]).strip()
        }
    # دالة تنفيذ الأمر
    def execute_command(self):
        for record in self:
            try:
                handler = getattr(self, f'_handle_{record.command_type}', None)
                if handler:
                    handler(record)
                    record.state = 'done'
                else:
                    raise ValueError(f"No handler for command type: {record.command_type}")
            except Exception as e:
                record.state = 'failed'
                _logger.error(f"Failed to execute command {record.id}: {str(e)}")
                
                
                
    @api.depends('command_type', 'command_data')
    def _compute_command_data(self):
        """توليد كود الأمر تلقائياً"""
        for cmd in self:
            print(self.id)
            print('opoooooo' , cmd.generate_command_code())
            cmd.command_data = cmd.generate_command_code()
    
    # @api.depends('command_type', 'create_date')
    # def _compute_name(self):
    #     """توليد اسم وصفي للأمر"""
    #     for cmd in self:
    #         type_label = dict(self.COMMAND_TYPES).get(cmd.command_type, '')
    #         cmd.name = f"{type_label} - {cmd.create_date}"
    
    def generate_command_code(self):
        """إنشاء كود الأمر حسب النوع"""
        cmd_id = self.id or 0
        data = json.loads(self.command_data or '{}')
        
        commands = {
            'reboot_device': f"C:{cmd_id}:REBOOT",
            'update_user': f"C:{cmd_id}:DATA UPDATE USERINFO PIN={data.get('pin')}",
            'delete_user': f"C:{cmd_id}:DATA DELETE USERINFO PIN={data.get('pin')}",
            'update_fingerprint': f"C:{cmd_id}:DATA UPDATE FP PIN={data.get('pin')} FID={data.get('fid')}",
            'update_face': f"C:{cmd_id}:DATA UPDATE FACE PIN={data.get('pin')} FID={data.get('fid')}",
            'update_userpic': f"C:{cmd_id}:DATA UPDATE USERPIC PIN={data.get('pin')}",
            'send_sms': f"C:{cmd_id}:DATA UPDATE SMS MSG={data.get('message')}",
            'query_attlog': f"C:{cmd_id}:DATA QUERY ATTLOG StartTime={data.get('start_time')} EndTime={data.get('end_time')}",
            'query_userinfo': f"C:{cmd_id}:DATA QUERY USERINFO PIN={data.get('pin')}",
            'clear_data': f"C:{cmd_id}:CLEAR LOG", 
            'جلب بيانات الحضور': f"C:332:DATA QUERY ATTLOG StartTime='05/21/2025 15:00:00' EndTime='05/27/2025 15:00:00'", 
            'بيانات المستخدم': f"C:333:DATA QUERY USERINFO PIN=1",
            'szسجلات المستخدم': f"C:344:DATA QUERY ATTLOG PIN=12 StartTime='05/21/2025 15:00:00' EndTime='05/27/2025 15:00:00'",
            'query_all_users': f"C:{cmd_id}:DATA QUERY USERINFO ALL",
        }
        
        # إضافة الحقول الاختيارية
        if self.command_type == 'update_user':
            commands['update_user'] += self._format_optional_fields(data, ['Name', 'Passwd', 'Card', 'Grp', 'Pri'])
        
        return commands.get(self.command_type, '')
    
    def _format_optional_fields(self, data, fields):
        """تنسيق الحقول الاختيارية للأوامر"""
        result = ''
        for field in fields:
            if field.lower() in data:
                result += f" {field}={data[field.lower()]}"
        return result
    
    def send_to_device(self):
        """إرسال الأمر إلى الجهاز"""
        for cmd in self:
            try:
                if cmd.state != 'draft':
                    continue
                
                cmd.device_id.message_post(body=f"تم إرسال الأمر: {cmd.command_code}")
                cmd.write({'state': 'pending'})
                _logger.info(f"تم إرسال الأمر {cmd.id} إلى الجهاز {cmd.device_id.serial_number}")
                
            except Exception as e:
                cmd.write({'state': 'failed', 'response': str(e)})
                _logger.error(f"فشل إرسال الأمر {cmd.id}: {str(e)}")