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
    
    def write(self, vals):
        return_value = super(IotFingerprintMachine, self).write(vals)
        if 'report_ids' in vals or ('type' in vals and vals.get('type') == 'biometric'):
            self.env['iot.channel'].update_is_open()
        return return_value

class IotFingerprintChannel(models.AbstractModel):
    _name = "iot.fingerprint.channel"
    _description = "The Websocket Iot Channel"

    SYSTEM_PARAMETER_KEY = 'iot.ws_channel'

    def _create_channel_if_not_exist(self):
        iot_channel = f'iot_channel-{secrets.token_hex(16)}'
        self.env['ir.config_parameter'].sudo().set_param(self.SYSTEM_PARAMETER_KEY, iot_channel)
        return iot_channel

    def get_iot_channel(self, check=False):
        """
        Get the IoT channel name.
        To facilitate multi-company, the channel is unique for every company and IoT

        :param check: If False, it will force to return the channel name even if it is unused.
        """
        if (self.env.is_system() or self.env.user._is_internal()) and (not check or self.update_is_open()):
            iot_channel_key_value = self.env['ir.config_parameter'].sudo().get_param(self.SYSTEM_PARAMETER_KEY)
            print("iot_channel_key_valueiot_channel_key_valueiot_channel_key_value",iot_channel_key_value)
            return iot_channel_key_value or self._create_channel_if_not_exist()
        return ''

    def update_is_open(self):
        """
        Wherever the IoT Channel should be open or not.
        For performance reasons, we only open the channel if there is at least one IoT device with a report set.

        :return: True if the channel should be open, False otherwise
        """

        has_report_device = bool(self.env['iot.device'].search_count([('report_ids', '!=', False)], limit=1))

        has_biometric_device = bool(self.env['iot.device'].search_count([('type', '=', 'biometric')], limit=1))

        is_open = has_report_device or has_biometric_device
        
        if not is_open:
            self.env["iot.box"].search([]).write({"is_websocket_active": False})
        return is_open