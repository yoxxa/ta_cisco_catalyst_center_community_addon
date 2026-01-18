import tempfile
import os

class Certificate:
    """Generates a temporary certificate file based on a .pem string"""
    def __init__(self, certificate_string: str) -> None:
        self.data: str = certificate_string
        self.temp_file: tempfile._TemporaryFileWrapper[str] = None

    def generate_temp_certificate_file(self) -> str:
        self.temp_file = tempfile.NamedTemporaryFile(mode="w", delete=False)
        self.temp_file.write(self.data)
        # file is still on the disk since delete=False
        self.temp_file.close()
        return self.temp_file.name

    def certificate(self, catalyst_center_conf_file: dict, input_item: dict):
        catc_certificate = catalyst_center_conf_file.get(input_item.get("catalyst_center")).get("dnac_certificate", None)
        if catc_certificate == None:
            cert = False
        else:
            cert = self.generate_temp_certificate_file()
        return cert

    def cleanup(self) -> None:
        """Deletes the certificate file on disk"""
        if (self.data != None):
            os.unlink(self.temp_file.name)
            self.temp_file = None