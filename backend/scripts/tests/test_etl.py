import importlib
import io
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import TestCase

from hue_portal.core.models import Office, Fine


class EtlLoaderTestCase(TestCase):
    def setUp(self):
        self.tempdir = TemporaryDirectory()
        self.data_dir = Path(self.tempdir.name)
        self._write_office_csv()
        self._write_fine_csv()

    def tearDown(self):
        self.tempdir.cleanup()
        os.environ.pop("ETL_DATA_DIR", None)

    def _write_office_csv(self):
        path = self.data_dir / "danh_ba_diem_tiep_dan.csv"
        path.write_text(
            "unit_name,address,district,working_hours,phone,email,latitude,longitude,service_scope,updated_at\n"
            "Công an phường A,123 Đường B,Quận 1,08:00-17:00,0123456789,ca@example.com,16.0,108.0,Tiếp dân,2025-01-01\n",
            encoding="utf-8"
        )

    def _write_fine_csv(self):
        path = self.data_dir / "muc_phat_theo_hanh_vi.csv"
        path.write_text(
            "violation_code,violation_name,article,decree,min_fine,max_fine,license_points,remedial_measures,source_url,updated_at\n"
            "V001,Vượt đèn đỏ,5,100/2019/NĐ-CP,1000000,3000000,2,Phạt bổ sung,http://example.com,2025-01-01\n",
            encoding="utf-8"
        )

    def _load_module(self):
        os.environ["ETL_DATA_DIR"] = str(self.data_dir)
        module = importlib.import_module("scripts.etl_load")
        return importlib.reload(module)

    def test_load_offices_creates_records(self):
        etl = self._load_module()
        log_buffer = io.StringIO()
        processed = etl.load_offices(since=None, dry_run=False, log_file=log_buffer)

        self.assertEqual(processed, 1)
        self.assertEqual(Office.objects.count(), 1)
        office = Office.objects.first()
        self.assertEqual(office.unit_name, "Công an phường A")

    def test_load_fines_creates_records(self):
        etl = self._load_module()
        log_buffer = io.StringIO()
        processed = etl.load_fines(since=None, dry_run=False, log_file=log_buffer)

        self.assertEqual(processed, 1)
        self.assertEqual(Fine.objects.count(), 1)
        fine = Fine.objects.first()
        self.assertEqual(fine.code, "V001")


if __name__ == "__main__":
    import unittest

    unittest.main()
