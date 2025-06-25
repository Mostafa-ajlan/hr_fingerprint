import { _t } from "@web/core/l10n/translation";
import { markup, onMounted, useState, onWillUpdateProps, useEffect } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ListController } from "@web/views/list/list_controller";
import { listView } from "@web/views/list/list_view";
import { handleBiometricIoTConnectionFallbacks } from "./iot_implement_action";
import {
    deleteConfirmationMessage,
    ConfirmationDialog,
} from "@web/core/confirmation_dialog/confirmation_dialog";


export class FingerprintUserListController extends ListController {

    setup() {
        super.setup(...arguments);
        this.action = useService("action");
        this.notification = useService("notification");
        this.orm = useService("orm");
    }

    /**
     * Main entry point for the deletion process. Shows a confirmation dialog to the user.
     */
    async onDeleteSelectedRecords() {
        this.dialogService.add(ConfirmationDialog, {
            body: _t(
                "Are you sure you want to delete these records? Users on IoT devices will also be deleted from the devices.",
            ),
            confirmLabel: _t("Delete"),
            confirm: () => this._processDeletion(),
            cancel: () => { },
        });
    }

    /**
     * Orchestrates the entire deletion process after user confirmation.
     * @param {Array} records - The records selected for deletion.
     */
    async _processDeletion() {
        const records = this.model.root.selection;
        // Ensure required fields are available in the view's data
        const iotRecordsToDelete = records.filter(
            (rec) => rec.data.connection_device_mode === "iot" && rec.data.active_user
        );

        const iotDeletionResults = await this._deleteUsersFromIoT(iotRecordsToDelete);

        const failedDeletions = iotDeletionResults.filter((res) => !res.success);
        console.log(failedDeletions, "failedDeletionsfailedDeletions")

        if (failedDeletions.length > 0) {
            this._handleIoTDeletionFailure(failedDeletions);
        } else {
            await this._deleteOdooRecords(records);
        }
    }

    /**
     * Handles the deletion of users from their associated IoT devices.
     * Groups users by IoT device and sends a single request per device.
     * @param {Array} iotRecords - Records of users to be deleted from IoT devices.
     * @returns {Promise<Array>} A promise that resolves to an array of result objects.
     */
    async _deleteUsersFromIoT(iotRecords) {

        // Step 1: Group users by their IoT device
        const deviceUserMap = {};
        for (const record of iotRecords) {
            const data = record.data;
            if (!data.device_id) continue;
            const deviceId = data.device_id[0];
            if (!deviceUserMap[deviceId]) {
                deviceUserMap[deviceId] = [];
            }
            deviceUserMap[deviceId].push({
                user_id: data.user_id,
                uid: data.uid,
                name: data.name,
            });
        }
        // Step 2: For each device, send a single delete request with all users
        const results = await Promise.all(
            Object.entries(deviceUserMap).map(async ([deviceId, users]) => {
                try {
                    // Get the IoT device identifier
                    const iotDeviceRecord = await this.orm.read(
                        "hr.fingerprint.device",
                        [parseInt(deviceId)],
                        ["iot_device_id"]
                    );

                    const iot_device_id = iotDeviceRecord[0].iot_device_id;
                    // Prepare the list of users to delete
                    const usersData = users.map(u => ({ user_id: u.user_id, uid: u.uid }));
                    // Send the delete request for all users on this device
                    await handleBiometricIoTConnectionFallbacks(this.env, this.orm, {
                        iot_device: iot_device_id,
                        action: "delete_users",
                        extraData: { users: usersData },
                    });
                    return { success: true, users: users };
                } catch (err) {
                    return {
                        success: false,
                        users: users,
                        error: err.data?.message || err.message || _t("Unknown error"),
                    };
                }
            })
        );

        // Flatten the results to user-level for error reporting
        const userResults = [];
        for (const res of results) {
            if (res.success) {
                for (const u of res.users) {
                    userResults.push({ success: true, name: u.name });
                }
            } else {
                for (const u of res.users) {
                    userResults.push({ success: false, name: u.name, error: res.error });
                }
            }
        }
        console.log("userResults", userResults);
        return userResults;
    }

    /**
     * Shows a detailed error dialog if any IoT deletions fail.
     * @param {Array} failedDeletions - An array of failed deletion result objects.
     */
    _handleIoTDeletionFailure(failedDeletions) {
        const errorMessages = failedDeletions
            .map((f) => _t("Could not delete user '%s': %s", f.name, f.error))
            .join("<br/>");

        this.dialogService.add(ConfirmationDialog, {
            title: _t("IoT Deletion Failed"),
            body: markup(
                _t(
                    "The following users could not be deleted from their IoT devices:<br/><br/>%s<br/><br/><b>No records have been deleted from Odoo.</b> Please resolve the issues and try again.",
                    errorMessages
                )
            ),
            confirm: () => { },
            cancel: () => { },
            confirmLabel: _t("OK"),
        });
    }

    /**
     * Deletes the records from Odoo and shows a success notification.
     * Records are split by connection mode to pass different contexts to the backend.
     * @param {Array} recordsToDelete - The full list of records to delete.
     */
    async _deleteOdooRecords(recordsToDelete) {
        const recordGroups = {
            iot: [],
            direct: [],
            other: [],
        };

        // Group records by their connection mode
        for (const record of recordsToDelete) {
            const mode = record.data.connection_device_mode;
            if (mode === "iot") {
                recordGroups.iot.push(record);
            } else if (mode === "direct") {
                recordGroups.direct.push(record);
            } else {
                recordGroups.other.push(record);
            }
        }

        const contextMap = {
            iot: { ...this.model.root.context, deletion_source: "iot" },
            direct: { ...this.model.root.context, deletion_source: "direct" },
            other: this.model.root.context,
        };

        let allDeletionsSuccessful = true;

        // Perform unlink for each group with its specific context
        for (const groupName in recordGroups) {
            const records = recordGroups[groupName];
            if (records.length === 0) {
                continue;
            }

            const resIds = records.map((r) => r.resId);
            const context = contextMap[groupName];

            const success = await this.orm.unlink(this.props.resModel, resIds, { context });
            if (!success) {
                allDeletionsSuccessful = false;
            }
        }

        if (!allDeletionsSuccessful) {
            this.notification.add(_t("Some records could not be deleted from Odoo."), {
                type: "danger",
            });
        } else {
            this.notification.add(
                _t("%s records have been successfully deleted.", recordsToDelete.length),
                { type: "success" }
            );
        }

        // Reload the view to reflect the changes.
        await this.model.load();
    }
}

export const fingerprintUserListController = {
    ...listView,
    Controller: FingerprintUserListController,
};

registry.category("views").add("fingerprint_user_list", fingerprintUserListController);


