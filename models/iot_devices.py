from odoo import api, fields, models

class IotFingerprintMachine(models.Model):
    _inherit = 'iot.device'

    type = fields.Selection(
        selection_add=[('biometric', 'Biometric Device')],
        ondelete={'biometric': 'cascade'}
    )

    # For Fingerprint devices
    ip_address = fields.Char(string='IP Address', readonly=True, help="IP address of the fingerprint device, if not set, the device will be detected automatically.")
    
    port = fields.Integer(string='Port', readonly=True, help="Port of the device, if not set, the device will be detected automatically.")
    
    password = fields.Char(string='Fingerprint Password', default='0', help="Fingerprint password of the device, if not set, the device will be detected automatically.")

    protocol = fields.Selection([
        ('tcp', 'TCP'),
        ('udp', 'UDP'),
    ], string='Protocol', readonly=True, default='tcp', help="Protocol of the device, if not set, the device will be detected automatically.")

    @api.model
    def get_iot_box_data(self, device_id, display_name = None):
        """
        """
        print("uutyutuytuyrtchgvcjh")
        device = self.browse(device_id[0])
        if device and device.type == 'biometric':
            create = False
            print(device.connected,"LKJLKJLKJLKJLKJLKJJKL")
            if not device.connected:
                fingerprint_device = self.env['hr.fingerprint.device'].search([('iot_device_id', '=', device.id)], limit=1)
                if not fingerprint_device:
                    print("WWWWWWWWWWWWWWWWW")
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

   