import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd


class SurveyFileToJSONConverter:
    ANSWER_BLOCKS = 16

    def __init__(self, file_path: str, sheet_name: Optional[str] = None):
        self.file_path = Path(file_path)
        self.sheet_name = 0 if sheet_name is None else sheet_name

    @staticmethod
    def _is_blank(value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, float) and math.isnan(value):
            return True
        return str(value).strip() == ""

    @staticmethod
    def _clean_str(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, float) and math.isnan(value):
            return ""
        return str(value).strip()

    @classmethod
    def _to_int(cls, value: Any, default: int = 0) -> int:
        if cls._is_blank(value):
            return default
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return default

    @classmethod
    def _to_float(cls, value: Any, default: float = 0.1) -> float:
        if cls._is_blank(value):
            return default
        try:
            val = float(value)
            return 0.1 if val == 0 else val
        except (ValueError, TypeError):
            return default

    @classmethod
    def _clean_image_url(cls, value: Any) -> str:
        value = cls._clean_str(value)
        if not value:
            return ""
        return value if value.lower().endswith(".png") else f"{value}.png"

    def _read_file(self) -> pd.DataFrame:
        suffix = self.file_path.suffix.lower()

        if suffix == ".csv":
            last_error = None
            for encoding in ("utf-8", "utf-8-sig", "cp1252", "latin1"):
                try:
                    df = pd.read_csv(self.file_path, sep=";", encoding=encoding)
                    break
                except UnicodeDecodeError as exc:
                    last_error = exc
            else:
                raise ValueError(
                    "Could not read CSV file. Please save it as UTF-8, CP1252, or Latin-1 encoded CSV."
                ) from last_error
        elif suffix in [".xlsx", ".xls", ".xlsm"]:
            df = pd.read_excel(self.file_path, sheet_name=self.sheet_name)
        else:
            raise ValueError("Unsupported file type. Use CSV, XLSX, XLSM, or XLS.")

        if isinstance(df, dict):
            raise ValueError("Excel upload must resolve to a single worksheet.")

        return df.fillna("")

    def _build_answer_from_block(self, row: pd.Series, n: int) -> Optional[Dict[str, Any]]:
        """
        n = 1..16

        Block 1 columns:
            Id, Text, value, minVal, minText, maxVal, maxText, stepSize, defaultValue
        Block 2+ columns:
            Id.1, Text.1, value.1, ...
        """
        suffix = "" if n == 1 else f".{n - 1}"
        id_key = f"Id{suffix}"

        if id_key not in row.index or self._is_blank(row[id_key]):
            return None

        return {
            "id": self._to_int(row.get(f"Id{suffix}")),
            "text": self._clean_str(row.get(f"Text{suffix}")),
            "value": self._to_float(row.get(f"value{suffix}")),
            "minVal": self._to_float(row.get(f"minVal{suffix}")),
            "minText": self._clean_str(row.get(f"minText{suffix}")),
            "maxVal": self._to_float(row.get(f"maxVal{suffix}")),
            "maxText": self._clean_str(row.get(f"maxText{suffix}")),
            "stepSize": self._to_float(row.get(f"stepSize{suffix}")),
            "defaultValue": self._to_float(row.get(f"defaultValue{suffix}")),
        }

    def _build_question(self, row: pd.Series) -> Dict[str, Any]:
        answers: List[Dict[str, Any]] = []

        for n in range(1, self.ANSWER_BLOCKS + 1):
            answer = self._build_answer_from_block(row, n)
            if answer:
                answers.append(answer)

        return {
            "id": self._to_int(row.get("id")),
            "active": self._to_int(row.get("active"), default=1),
            "title": self._clean_str(row.get("title")),
            "subText": self._clean_str(row.get("subText")),
            "imageURL": self._clean_image_url(row.get("imageURL")),
            "frequency": self._to_int(row.get("frequency")),
            "clockTime": self._to_int(row.get("clockTime")),
            "nextDayToAnswer": self._to_int(row.get("nextDayToAnswer")),
            "category": self._to_int(row.get("category")),
            "activate_question": self._parse_question_refs(row.get("activate_question")),
            "deactivate_question": self._parse_question_refs(row.get("deactivate_question", row.get("deActivate_question"))),
            "clockTime_start": self._clean_str(row.get("clockTime_start")),
            "clockTime_end": self._clean_str(row.get("clockTime_end")),
            "activation_condition": self._clean_str(row.get("activation_condition")),
            "deactivation_condition": self._clean_str(row.get("deactivation_condition"), row.get("deActivation_condition")),
            "url": self._clean_str(row.get("url")),
            "questionType": self._to_int(row.get("questionType")),
            "deactivateOnAnswer": self._clean_str(row.get("deactivateOnAnswer")),
            "deactivateOnDate": self._to_int(row.get("deactivateOnDate")),
            "answer": answers,
        }

    def _parse_question_refs(self, value):
        value = self._clean_str(value)

        if value in ("", "[]"):
            return []

        value = value.replace(";", ",")

        return [
            int(v.strip())
            for v in value.split(",")
            if v.strip()
        ]

    def to_dict(self) -> Dict[str, Any]:
        df = self._read_file()

        survey = {
            "topN": -1,
            "questions": [],
        }

        for _, row in df.iterrows():
            survey["questions"].append(self._build_question(row))

        return survey

    def to_json(self, pretty: bool = True) -> str:
        data = self.to_dict()
        if pretty:
            return json.dumps(data, ensure_ascii=False, indent=2)
        return json.dumps(data, ensure_ascii=False)

    def save_json(self, output_path: str, pretty: bool = True) -> None:
        json_str = self.to_json(pretty=pretty)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(json_str)
