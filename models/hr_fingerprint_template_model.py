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
    _description = 'Fingerprint Template'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    device_id = fields.Many2one(
        'hr.fingerprint.device', 
        string='Device', 
        required=True,
        ondelete='cascade',
    )
    user_id = fields.Many2one(
        'hr.fingerprint.user', 
        string='User', 
        required=True,
        ondelete='cascade',
    )
    
    fingerprint_id = fields.Integer(string='Fingerprint ID', required=True,)
    template = fields.Binary(string='Template', required=True,)
    mark = fields.Binary(string='Mark')
    
    size = fields.Integer(string='Size',)
    valid = fields.Integer(string='Valid', default=1)
    display_name = fields.Char(string='Display Name', compute='_compute_display_name', store=True)
    finger_name = fields.Selection([
        ('0', 'Right Thumb'),
        ('1', 'Right Index Finger'),
        ('2', 'Right Middle Finger'),
        ('3', 'Right Ring Finger'),
        ('4', 'Right Little Finger'),
        ('5', 'Left Thumb'),
        ('6', 'Left Index Finger'),
        ('7', 'Left Middle Finger'),
        ('8', 'Left Ring Finger'),
        ('9', 'Left Little Finger'),
    ], string='Finger Name', compute='_compute_finger_name', store=True)
    
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