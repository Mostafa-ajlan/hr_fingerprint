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
    cmd_id = fields.Char(string="CmdId", readonly=True, default='New')
    user_ids = fields.Many2one('hr.fingerprint.user',string="User IDs", help="User ID in the fingerprint device")
    user_id = fields.Char(related='user_ids.user_id',string="User ID",)
    name_value = fields.Char(string="User Name")
    password = fields.Char(string="Password")
    card = fields.Char(string="Card")
    group_id = fields.Char(string="Group")
    tz = fields.Char(string="Time Period")
    active_user = fields.Boolean(default=True)
    privilege = fields.Selection([
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
        'command_type', 'cmd_id', 'user_id', 'name_value', 'password', 'card', 'group_id', 'tz', 'privilege',
        'photo_size', 'photo_content', 'sms_message', 'sms_tag', 'sms_uid', 'sms_min', 'sms_start_time',
        'start_time', 'end_time', 'option_key', 'option_value', 'fp_id', 'retry', 'overwrite', 'shell_cmd'
    )
    def _compute_generated_command(self):
        for rec in self:
            c = rec.cmd_id or '1'
            u = rec.user_id or ''
            if rec.command_type == 'update_userinfo':
                rec.generated_command = (
                    f'C:{c}:DATA UPDATE USERINFO\t'
                    f'PIN={u}\tName={rec.name_value}\tPasswd={rec.password}\t'
                    f'Card={rec.card}\tGrp={rec.group_id}\tTZ={rec.tz}\tPri={rec.privilege}'
                )
            elif rec.command_type == 'update_userpic':
                rec.generated_command = (
                    f'C:{c}:DATA UPDATE USERPIC\t'
                    f'PIN={u}\tSize={rec.photo_size}\tContent={rec.photo_content}'
                )
            elif rec.command_type == 'update_sms':
                rec.generated_command = (
                    f'C:{c}:DATA UPDATE SMS\t'
                    f'MSG={rec.sms_message}\tTAG={rec.sms_tag}\tUID={rec.sms_uid}\t'
                    f'MIN={rec.sms_min}\tStartTime={rec.sms_start_time}'
                )
            elif rec.command_type == 'delete_userinfo':
                rec.generated_command = f'C:{c}:DATA DELETE USERINFO\tPIN={u}'
            elif rec.command_type == 'delete_sms':
                rec.generated_command = f'C:{c}:DATA DELETE SMS\tUID={rec.sms_uid}'
            elif rec.command_type == 'query_attlog':
                rec.generated_command = (
                    f'C:{c}:DATA QUERY ATTLOG\t'
                    f'StartTime={rec.start_time}\tEndTime={rec.end_time}'
                )
            elif rec.command_type == 'query_userinfo':
                rec.generated_command = f'C:{c}:DATA QUERY USERINFO\tPIN={u}'
            elif rec.command_type == 'query_userpic':
                rec.generated_command = f'C:{c}:DATA QUERY USERPIC\tPIN={u}'
            elif rec.command_type == 'clear_log':
                rec.generated_command = f'C:{c}:CLEAR LOG'
            elif rec.command_type == 'clear_data':
                rec.generated_command = f'C:{c}:CLEAR DATA'
            elif rec.command_type == 'check':
                rec.generated_command = f'C:{c}:CHECK'
            elif rec.command_type == 'log':
                rec.generated_command = f'C:{c}:LOG'
            elif rec.command_type == 'verify_sum':
                rec.generated_command = (
                    f'C:{c}:VERIFY SUM ATTLOG\t'
                    f'StartTime={rec.start_time}\tEndTime={rec.end_time}'
                )
            elif rec.command_type == 'set_option':
                rec.generated_command = f'C:{c}:SET OPTION {rec.option_key}={rec.option_value}'
            elif rec.command_type == 'reload_option':
                rec.generated_command = f'C:{c}:RELOAD OPTIONS'
            elif rec.command_type == 'info':
                rec.generated_command = f'C:{c}:INFO'
            elif rec.command_type == 'enroll_fp':
                rec.generated_command = (
                    f'C:{c}:ENROLL_FP\tPIN={u}\tFID={rec.fp_id}\tRETRY={rec.retry}\tOVERWRITE={rec.overwrite}'
                )
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

    # other fields...

    @api.model
    def create(self, vals):
        if vals.get('cmd_id', 'New') == 'New':
            vals['cmd_id'] = self.env['ir.sequence'].next_by_code('zk.device.command') or 'New'
        return super(ZKDeviceCommand, self).create(vals)