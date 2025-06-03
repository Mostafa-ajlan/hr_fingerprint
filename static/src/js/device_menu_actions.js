/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { ListController } from "@web/views/list/list_controller";
import { _t } from "@web/core/l10n/translation";

export const patchFormControllerFingerprintActions = {
    getStaticActionMenuItems() {
        const menuItems = super.getStaticActionMenuItems();
        // إنشاء قائمة متداخلة رئيسية

        const record = this.model.root;
        const actions = [
            { key: 'fetch_user', sequence: 45, icon: 'fa fa-user-circle', descriptions: 'Fetch Users' },
            { key: 'download_attendance', sequence: 46, icon: 'fa fa-download', descriptions: 'Download Attendance' },
            { key: 'download_template', sequence: 47, icon: 'fa fa-download', descriptions: 'Download Template' }
        ];

        actions.forEach(item => {
            menuItems[item.key] = {
                sequence: item.sequence,
                description: _t(item.descriptions),
                callback: async () => {
                    try {
                        await this.executeFingerprintAction(item.key, record);
                    } catch (error) {
                        console.error(`Error executing ${item.key}:`, error);
                        this.env.services.notification.add(
                            `Failed to execute ${item.key}: ${error.message}`,
                            { type: 'danger' }
                        );
                    }
                },
                icon: item.icon,
                group: 'fingerprint_device_actions',
                isAvailable: () => this.isActionAvailable(item.key, record),
            };
        });

        return menuItems;
    },

    async executeFingerprintAction(actionName, record) {
        console.log("UTURURYTRYTRTUIYOIYOIYIUTTYYRTYR")
    },

    isActionAvailable(action, record) {
        if (!record || !record.resId) return false;
        // الحصول على اسم النموذج الحالي
        const modelName = this.props.resModel;
        console.log("hhhhhhhhhhhhhhhhhhhhhh", modelName)

        // تحديد النماذج المسموح بها
        const allowedModels = [
            'hr.fingerprint.device', // نموذج الموظفين
        ];
        // التحقق مما إذا كان النموذج الحالي مسموحاً به
        return allowedModels.includes(modelName);
    },

};

patch(FormController.prototype, patchFormControllerFingerprintActions);