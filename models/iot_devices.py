from odoo import api, fields, models , _

class IotFingerprintMachine(models.Model):
    _inherit = 'iot.device'

    type = fields.Selection(
        selection_add=[('biometric', _('Biometric Device'))],
        ondelete={'biometric': 'cascade'}
    )

    # For Fingerprint devices
    ip_address = fields.Char(string=_("IP Address"), readonly=True, help=_("IP address of the fingerprint device, if not set, the device will be detected automatically."))

    port = fields.Integer(string=_("Port"), readonly=True, help=_("Port of the device, if not set, the device will be detected automatically."))

    password = fields.Char(string=_("Fingerprint Password"), default='0', help=_("Fingerprint password of the device, if not set, the device will be detected automatically."))

    protocol = fields.Selection([
        ('tcp', 'TCP'),
        ('udp', 'UDP'),
    ], string=_('Protocol'), readonly=True, default='tcp', help=_("Protocol of the device, if not set, the device will be detected automatically."))

    @api.model
    def get_iot_box_data(self, device_id, display_name = None):
        """
        """
        device = self.browse(device_id[0])
        if device and device.type == 'biometric':
            create = False
            if not device.connected:
                fingerprint_device = self.env['hr.fingerprint.device'].search([('iot_device_id', '=', device.id)], limit=1)
                if not fingerprint_device:
                    self.env['hr.fingerprint.device'].create({
                        'name': display_name if display_name else device.name,
                        'connection_mode': 'iot',
                        'connection_type': device.connection,
                        'ip_address': device.ip_address,
                        'port': device.port,
                        'password': device.password,
                        'protocol': device.protocol,
                        'iot_device_id': device.id,
                    })
                    create = True  

            # For biometric devices, we need to return the IP address and port
            return {
                'iot_id': device.iot_id.id,
                'iot_ip': device.iot_ip,
                'iot_name': device.iot_id.name,
                'identifier': device.identifier,
                'name': device.name,
                'ip_address': device.ip_address,
                'port': device.port,
                'password': device.password,
                'protocol': device.protocol,
                'connected': device.connected,
                'create': create,
            }
        return False

   