from odoo import models, fields, api
import logging
import json


_logger = logging.getLogger(__name__)

class ZKDeviceCommand(models.Model):
    _name = 'zk.device.command'
    _description = 'zk Device Command'
    _order = 'create_date desc'
    
    name = fields.Char(string='Name', required=True)
    command_type = fields.Selection([
        ('update_userinfo', 'Update User Info'),
        ('update_userpic', 'Update User Photo'),
        ('update_sms', 'Send SMS'),
        ('delete_userinfo', 'Delete User Info'),
        ('delete_sms', 'Delete SMS'),
        ('query_attlog', 'Query Attendance Log'),
        ('query_userinfo', 'Query User Info'),
        ('query_userpic', 'Query User picture'),
        ('clear_log', 'Clear Log'),
        ('clear_data', 'Clear Data'),
        ('check', 'Check'),
        ('log', 'Log'),
        ('verify_sum', 'Verify Attendance Sum'),
        ('set_option', 'Set Option'),
        ('reload_option', 'Reload Option'),
        ('info', 'Info'),
        ('enroll_fp', 'Enroll Fingerprint'),
        ('reboot', 'Reboot'),
        ('unlock', 'Unlock Door'),
        ('unalarm', 'Unalarm'),
        ('shell', 'Shell Command'),
    ], string='Command Type', required=True)

    # Shared fields
    device_id = fields.Many2one('hr.fingerprint.device', 'Device', required=True)
    cmd_id = fields.Char(string="CmdId")
    user_ids = fields.Many2one('hr.fingerprint.user',string="User IDs", help="User ID in the fingerprint device")
    user_id = fields.Char(related='user_ids.user_id',string="User ID",)
    name_value = fields.Char(string="Name")
    passwd = fields.Char(string="Password")
    card = fields.Char(string="Card")
    group = fields.Char(string="Group")
    tz = fields.Char(string="Time Period")
    pri = fields.Selection([
        ('0', 'Normal User'),
        ('2', 'Registrar'),
        ('6', 'Admin'),
        ('10', 'User-defined'),
        ('14', 'Super Admin')
    ], string="Privilege")
    state = fields.Selection([
        ('draft', 'مسودة'),
        ('pending', 'معلق'),
        ('sent', 'تم الإرسال'),
        ('done', 'مكتمل'),
        ('failed', 'فشل')
    ], string='الحالة', default='draft')
    # Photo command
    photo_size = fields.Char(string="Photo Size (Base64 length)")
    photo_content = fields.Text(string="Photo Content (Base64)")

    # SMS command
    sms_message = fields.Char(string="SMS Message")
    sms_tag = fields.Selection([
        ('253', 'Public'),
        ('254', 'User'),
        ('255', 'Reserved')
    ], string="SMS Tag")
    sms_uid = fields.Char(string="Message Number")
    sms_min = fields.Char(string="Duration (Min)")
    sms_start_time = fields.Datetime(string="Start Time")

    # QUERY/VERIFY
    start_time = fields.Datetime(string="Start Time")
    end_time = fields.Datetime(string="End Time")

    # Option
    option_key = fields.Char(string="Option Key")
    option_value = fields.Char(string="Option Value")

    # Enroll FP
    fp_id = fields.Char(string="Fingerprint ID")
    retry = fields.Integer(string="Retry Count")
    overwrite = fields.Selection([('0', 'No'), ('1', 'Yes')], string="Overwrite?")

    # Shell
    shell_cmd = fields.Char(string="Shell Command")

    # Final command output
    generated_command = fields.Text(string="Generated Command", compute="_compute_generated_command", store=True)
    execution_date = fields.Datetime(string='Execution Date')
    @api.depends(
        'command_type', 'cmd_id', 'user_id', 'name_value', 'passwd', 'card', 'group', 'tz', 'pri',
        'photo_size', 'photo_content', 'sms_message', 'sms_tag', 'sms_uid', 'sms_min', 'sms_start_time',
        'start_time', 'end_time', 'option_key', 'option_value', 'fp_id', 'retry', 'overwrite', 'shell_cmd'
    )
    def _compute_generated_command(self):
        for rec in self:
            c = rec.cmd_id or '1'
            u = rec.user_id or ''
            if rec.command_type == 'update_userinfo':
                rec.generated_command = f'C:{c}:DATA UPDATE USERINFO PIN={u} Name={rec.name_value} Passwd={rec.passwd} Card={rec.card} Grp={rec.group} TZ={rec.tz} Pri={rec.pri}'
            elif rec.command_type == 'update_userpic':
                rec.generated_command = f'C:{c}:DATA UPDATE USERPIC PIN={u} Size={rec.photo_size} Content={rec.photo_content}'
            elif rec.command_type == 'update_sms':
                rec.generated_command = f'C:{c}:DATA UPDATE SMS MSG={rec.sms_message} TAG={rec.sms_tag} UID={rec.sms_uid} MIN={rec.sms_min} StartTime={rec.sms_start_time}'
            elif rec.command_type == 'delete_userinfo':
                rec.generated_command = f'C:{c}:DATA DELETE USERINFO PIN={u}'
            elif rec.command_type == 'delete_sms':
                rec.generated_command = f'C:{c}:DATA DELETE SMS UID={rec.sms_uid}'
            elif rec.command_type == 'query_attlog':
                rec.generated_command = f'C:{c}:DATA QUERY ATTLOG StartTime={rec.start_time} EndTime={rec.end_time}'
            elif rec.command_type == 'query_userinfo':
                rec.generated_command = f'C:{c}:DATA QUERY USERINFO PIN={u}'
            elif rec.command_type == 'query_userpic':
                rec.generated_command = f'C:{c}:DATA QUERY USERPIC PIN={u}'
            elif rec.command_type == 'clear_log':
                rec.generated_command = f'C:{c}:CLEAR LOG'
            elif rec.command_type == 'clear_data':
                rec.generated_command = f'C:{c}:CLEAR DATA'
            elif rec.command_type == 'check':
                rec.generated_command = f'C:{c}:CHECK'
            elif rec.command_type == 'log':
                rec.generated_command = f'C:{c}:LOG'
            elif rec.command_type == 'verify_sum':
                rec.generated_command = f'C:{c}:VERIFY SUM ATTLOG StartTime={rec.start_time} EndTime={rec.end_time}'
            elif rec.command_type == 'set_option':
                rec.generated_command = f'C:{c}:SET OPTION {rec.option_key}={rec.option_value}'
            elif rec.command_type == 'reload_option':
                rec.generated_command = f'C:{c}:RELOAD OPTIONS'
            elif rec.command_type == 'info':
                rec.generated_command = f'C:{c}:INFO'
            elif rec.command_type == 'enroll_fp':
                rec.generated_command = f'C:{c}:ENROLL_FP PIN={u} FID={rec.fp_id} RETRY={rec.retry} OVERWRITE={rec.overwrite}'
            elif rec.command_type == 'reboot':
                rec.generated_command = f'C:{c}:REBOOT'
            elif rec.command_type == 'unlock':
                rec.generated_command = f'C:{c}:AC_UNLOCK'
            elif rec.command_type == 'unalarm':
                rec.generated_command = f'C:{c}:AC_UNALARM'
            elif rec.command_type == 'shell':
                rec.generated_command = f'C:{c}:SHELL {rec.shell_cmd}'
            else:
                rec.generated_command = 'Unknown command'