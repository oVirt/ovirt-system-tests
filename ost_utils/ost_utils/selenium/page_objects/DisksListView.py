import logging

from .EntityListView import *

LOGGER = logging.getLogger(__name__)


class DisksListView(EntityListView):

    def __init__(self, ovirt_driver):
        super(DisksListView, self).__init__(ovirt_driver,
                'disks', ['Storage', 'Disks'], 'MainDiskView_table_content_col0_row')

    def is_new_button_enabled(self):
        return self.ovirt_driver.is_button_enabled('New')

    def is_edit_button_enabled(self):
        return self.ovirt_driver.is_button_enabled('Edit')

    def is_remove_button_enabled(self):
        return self.ovirt_driver.is_button_enabled('Remove')

    def is_move_button_enabled(self):
        return self.ovirt_driver.is_button_enabled('Move')

    def is_copy_button_enabled(self):
        return self.ovirt_driver.is_button_enabled('Copy')

    def is_upload_button_enabled(self):
        return self.ovirt_driver.is_button_enabled('Upload')

    def upload(self, image_local_path, image_name):
        LOGGER.debug(f'Upload image from local path {image_local_path}')

        self.ovirt_driver.id_click('ActionPanelView_Upload')
        self.ovirt_driver.action_on_element('Start', 'click')
        self.ovirt_driver.action_on_element('UploadImagePopupView_fileUpload', 'send',
                image_local_path)
        self.ovirt_driver.action_on_element('VmDiskPopupWidget_alias', 'send',
                image_name)
        self.ovirt_driver.wait_for_id('UploadImagePopupView_Ok').click()
        self.ovirt_driver.wait_long_until('Waiting for disk to appear in disk list',
                lambda: image_name in self.get_entities())
