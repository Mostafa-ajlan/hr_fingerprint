import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

try:
    from zk import ZK, const
except ImportError:
    _logger.error("Please install pyzk library: pip install pyzk")

class HrFingerprintTemplate(models.Model): 
    _name = 'hr.fingerprint.template'
    _description = _("Fingerprint Template")
    _inherit = ['mail.thread', 'mail.activity.mixin']

    device_id = fields.Many2one(
        'hr.fingerprint.device', 
        string=_('Device'), 
        required=True,
        ondelete='cascade',
    )
    user_id = fields.Many2one(
        'hr.fingerprint.user', 
        string=_('User'), 
        required=True,
        ondelete='cascade',
    )

    fingerprint_id = fields.Integer(string=_('Fingerprint ID'), required=True,)
    template = fields.Binary(string=_('Template'), required=True,)
    mark = fields.Binary(string=_('Mark'))

    size = fields.Integer(string=_('Size'),)
    valid = fields.Integer(string=_('Valid'), default=1)
    display_name = fields.Char(string=_('Display Name'), compute='_compute_display_name', store=True)
    finger_name = fields.Selection([
        ('0', _('Right Thumb')),
        ('1', _('Right Index Finger')),
        ('2', _('Right Middle Finger')),
        ('3', _('Right Ring Finger')),
        ('4', _('Right Little Finger')),
        ('5', _('Left Thumb')),
        ('6', _('Left Index Finger')),
        ('7', _('Left Middle Finger')),
        ('8', _('Left Ring Finger')),
        ('9', _('Left Little Finger')),
    ], string=_('Finger Name'), compute='_compute_finger_name', store=True)

    @api.depends('fingerprint_id')
    def _compute_finger_name(self):
        for template in self:
            if template.fingerprint_id >= 0 and template.fingerprint_id <= 9:
                template.finger_name = str(template.fingerprint_id)
            else:
                template.finger_name = False

    @api.depends('user_id.name', 'finger_name')
    def _compute_display_name(self):
        for template in self:
            if template.user_id and template.finger_name:
                finger_name = dict(template._fields['finger_name'].selection).get(template.finger_name)
                template.display_name = f"{template.user_id.name} - {finger_name}"
            else:
                template.display_name = f"Template {template.id}"            