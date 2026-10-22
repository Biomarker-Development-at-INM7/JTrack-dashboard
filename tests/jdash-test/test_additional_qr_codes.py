from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from jdash.services.subject import Subject
from jdash.utils.SubjectPDF import SubjectPDF


class AdditionalQrCodeTests(SimpleTestCase):
    def test_subject_pdf_renders_requested_activation_range(self):
        markup = SubjectPDF("Study").qr_codes("/tmp/Study_00001", 5, 8)

        for activation in range(5, 9):
            self.assertIn(f"Activation {activation}", markup)
            self.assertIn(f"Study_00001_{activation}.png", markup)
        self.assertNotIn("Activation 4", markup)

    @override_settings(DASH_FOLDER="/tmp/jdash-additional-qr-test")
    @patch("jdash.services.subject.Subject.write_pdf")
    @patch("jdash.services.subject.qrcode.QRCode")
    @patch("jdash.services.subject.os.path.isfile")
    def test_add_qr_activations_generates_five_through_eight(
        self,
        mock_isfile,
        mock_qr_code,
        mock_write_pdf,
    ):
        mock_isfile.side_effect = lambda path: path.endswith("Study_00001.pdf")
        image = MagicMock()
        mock_qr_code.return_value.make_image.return_value = image

        Subject.add_qr_activations("Study", "Study_00001")

        self.assertEqual(image.save.call_count, 4)
        saved_paths = [call.args[0] for call in image.save.call_args_list]
        for activation in range(5, 9):
            self.assertTrue(any(path.endswith(f"Study_00001_{activation}.png") for path in saved_paths))
        mock_write_pdf.assert_called_once_with(
            "Study",
            "Study_00001",
            additional_activation_range=(5, 8),
        )

    @override_settings(DASH_FOLDER="/tmp/jdash-additional-qr-test")
    @patch("jdash.services.subject.os.chmod")
    @patch("jdash.services.subject.os.replace")
    @patch("jdash.services.subject.os.path.exists", return_value=False)
    @patch("jdash.services.subject.pdfkit.from_string")
    def test_write_pdf_adds_second_page(
        self,
        mock_pdfkit,
        _mock_exists,
        mock_replace,
        mock_chmod,
    ):
        Subject.write_pdf("Study", "Study_00001", additional_activation_range=(5, 8))

        markup, temporary_path = mock_pdfkit.call_args.args[:2]
        self.assertIn('page-break-before: always', markup)
        self.assertIn("Activation 1", markup)
        self.assertIn("Activation 5", markup)
        self.assertIn("Activation 8", markup)
        self.assertTrue(temporary_path.endswith("Study_00001.pdf.tmp.pdf"))
        final_path = temporary_path.removesuffix(".tmp.pdf")
        mock_replace.assert_called_once_with(temporary_path, final_path)
        mock_chmod.assert_called_once_with(final_path, 0o0775)

    def test_add_qr_activations_rejects_another_study_subject(self):
        with self.assertRaises(ValueError):
            Subject.add_qr_activations("Study", "AnotherStudy_00001")
