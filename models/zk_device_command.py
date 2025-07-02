from odoo import models, fields, api , _
import logging
import json


_logger = logging.getLogger(__name__)

class ZKDeviceCommand(models.Model):
    _name = 'zk.device.command'
    _description = _("zk Device Command")
    _order = 'create_date desc'

    name = fields.Char(string=_('Name'), required=True)
    command_type = fields.Selection([
        ('update_userinfo', _('Update User Info')),
        ('update_userpic', _('Update User Photo')),
        ('update_sms', _('Send SMS')),
        ('delete_userinfo', _('Delete User Info')),
        ('delete_sms', _('Delete SMS')),
        ('download_attendance', _('Query Attendance Log')),
        ('fetch_user', _('Query User Info')),
        ('download_template', _('Query User picture')),
        ('clear_log', _('Clear Log')),
        ('clear_data', _('Clear Data')),
        ('check', _('Check')),
        ('log', _('Log')),
        ('verify_sum', _('Verify Attendance Sum')),
        ('set_option', _('Set Option')),
        ('reload_option', _('Reload Option')),
        ('info', _('Info')),
        ('enroll_fp', _('Enroll Fingerprint')),
        ('reboot_device', _('Reboot')),
        ('shutdown_device', _('Shutdown Device')),
        ('unlock', _('Unlock Door')),
        ('unalarm', _('Unalarm')),
        ('shell', _('Shell Command')),
    ], string=_('Command Type'), required=True)

    # Shared fields
    device_id = fields.Many2one('hr.fingerprint.device', 'Device', required=True)
    cmd_id = fields.Char(string="CmdId", readonly=True, default='New')
    user_ids = fields.Many2one('hr.fingerprint.user',string="User IDs", help="User ID in the fingerprint device")
    user_id = fields.Char(related='user_ids.user_id',string="User ID",readonly=False)
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
        ('draft', _("Draft")),
        ('pending', _("Pending")),
        ('sent', _("Sent")),
        ('done', _("Done")),
        ('failed', _("Failed"))
    ], string=_("State"), default='draft')
    # Photo command
    photo_size = fields.Char(string=_("Photo Size (Base64 length)"))
    photo_content = fields.Text(string=_("Photo Content (Base64)"))

    # SMS command
    sms_message = fields.Char(string=_("SMS Message"))
    sms_tag = fields.Selection([
        ('253', _('Public')),
        ('254', _('User')),
        ('255', _('Reserved'))
    ], string=_("SMS Tag"))
    sms_uid = fields.Char(string=_("Message Number"))
    sms_min = fields.Char(string=_("Duration (Min)"))
    sms_start_time = fields.Datetime(string=_("Start Time"))

    # QUERY/VERIFY
    start_time = fields.Datetime(string=_("Start Time"))
    end_time = fields.Datetime(string=_("End Time"))

    # Option
    option_key = fields.Char(string=_("Option Key"))
    option_value = fields.Char(string=_("Option Value"))

    # Enroll FP
    fp_id = fields.Char(string=_("Fingerprint ID"))
    retry = fields.Integer(string=_("Retry Count"))
    overwrite = fields.Selection([('0', _('No')), ('1', _('Yes'))], string=_("Overwrite?"))

    # Shell
    shell_cmd = fields.Char(string=_("Shell Command"))

    _constraint= [
        ('unique_cmd_id', 'cmd_id', 'cmd_id', 'Command ID must be unique'),]
    # Final command output
    generated_command = fields.Text(string=_("Generated Command"), compute="_compute_generated_command", store=True)
    execution_date = fields.Datetime(string=_("Execution Date"))
    @api.depends(
        'command_type', 'cmd_id', 'user_id', 'name_value', 'password', 'card', 'group_id', 'tz', 'privilege',
        'photo_size', 'photo_content', 'sms_message', 'sms_tag', 'sms_uid', 'sms_min', 'sms_start_time',
        'start_time', 'end_time', 'option_key', 'option_value', 'fp_id', 'retry', 'overwrite', 'shell_cmd'
    )
    def _compute_generated_command(self):
        for rec in self:
            c = rec.cmd_id or '1'
            u = f'PIN={rec.user_id}' if rec.user_id else ''
            name = f'Name={rec.name_value}' if rec.name_value else ''
            Passwd = f'Passwd={rec.password}' if rec.password else ''
            card = f'Card={rec.card}' if rec.card else ''
            group = f'Grp={rec.group_id}' if rec.group_id else ''
            tz = f'TZ={rec.tz}' if rec.tz else ''
            privilege = f'Pri={rec.privilege}' if rec.privilege else ''
            photo_size = f'Size={rec.photo_size}' if rec.photo_size else ''
            photo_content = f'Content={rec.photo_content}' if rec.photo_content else ''
            sms_message = f'MSG={rec.sms_message}' if rec.sms_message else ''
            sms_tag = f'TAG={rec.sms_tag}' if rec.sms_tag else ''
            sms_uid = f'UID={rec.sms_uid}' if rec.sms_uid else ''
            sms_min = f'MIN={rec.sms_min}' if rec.sms_min else ''
            sms_start_time = f'StartTime={rec.sms_start_time}' if rec.sms_start_time else ''
            start_time = f'StartTime={rec.start_time}' if rec.start_time else ''
            end_time = f'EndTime={rec.end_time}' if rec.end_time else ''
            option_key = f'Key={rec.option_key}' if rec.option_key else ''
            option_value = f'Value={rec.option_value}' if rec.option_value else ''
            fp_id = f'FID={rec.fp_id}' if rec.fp_id else ''
            retry = f'RETRY={rec.retry}' if rec.retry else ''
            overwrite = f'OVERWRITE={rec.overwrite}' if rec.overwrite else ''
            shell_cmd = rec.shell_cmd or ''
            if rec.command_type == 'update_userinfo':
                rec.generated_command = (
                    f'C:{c}:DATA UPDATE USERINFO\t'
                    f'{u}\t{name}\t{Passwd}\t'
                    f'{card}\t{group}\t{tz}\t{privilege}'
                )
            elif rec.command_type == 'update_userpic':
                rec.generated_command = (
                    f'C:{c}:DATA UPDATE USERPIC\t'
                    f'{u}\t{photo_size}\t{photo_content}'
                )
            elif rec.command_type == 'update_sms':
                rec.generated_command = (
                    f'C:{c}:DATA UPDATE SMS\t'
                    f'{sms_message}\t{sms_tag}\t{sms_uid}\t'
                    f'{sms_min}\t{sms_start_time}'
                )
            elif rec.command_type == 'delete_userinfo':
                rec.generated_command = f'C:{c}:DATA DELETE USERINFO\t{u}'
            elif rec.command_type == 'delete_sms':
                rec.generated_command = f'C:{c}:DATA DELETE SMS\t{sms_uid}'
            elif rec.command_type == 'download_attendance':
                rec.generated_command = (
                    f'C:{c}:DATA QUERY ATTLOG\t'
                    f'{start_time}\t{end_time}'
                )
            elif rec.command_type == 'fetch_user':
                rec.generated_command = f'C:{c}:DATA QUERY USERINFO\t{u}'
            elif rec.command_type == 'download_template':
                rec.generated_command = f'C:{c}:DATA QUERY USERPIC\t{u}'
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
                    f'{start_time}\t{end_time}'
                )
            elif rec.command_type == 'set_option':
                rec.generated_command = f'C:{c}:SET OPTION {option_key}={option_value}'
            elif rec.command_type == 'reload_option':
                rec.generated_command = f'C:{c}:RELOAD OPTIONS'
            elif rec.command_type == 'info':
                rec.generated_command = f'C:{c}:INFO'
            elif rec.command_type == 'enroll_fp':
                rec.generated_command = (
                    f'C:{c}:ENROLL_FP\tPIN={u}\t{fp_id}\t{retry}\t{overwrite}'
                )
            elif rec.command_type == 'reboot_device':
                rec.generated_command = f'C:{c}:REBOOT'
            elif rec.command_type == 'unlock':
                rec.generated_command = f'C:{c}:AC_UNLOCK'
            elif rec.command_type == 'unalarm':
                rec.generated_command = f'C:{c}:AC_UNALARM'
            elif rec.command_type == 'shell':
                rec.generated_command = f'C:{c}:SHELL {shell_cmd}'
            else:
                rec.generated_command = 'Unknown command'

    # other fields...

    @api.model
    def create(self, vals):
        if vals.get('cmd_id', 'New') == 'New':
            vals['cmd_id'] = self.env['ir.sequence'].next_by_code('zk.device.command') or 'New'
        return super(ZKDeviceCommand, self).create(vals)