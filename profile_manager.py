"""Local profile persistence for TOTP Clipboard."""

from __future__ import annotations

import json
import os
import shutil
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import win32crypt

from otp_service import validate_secret


APP_DIR = Path(__file__).resolve().parent
APP_DATA_DIR = Path(os.environ.get("APPDATA", Path.home())) / "TOTP Clipboard"
DEFAULT_PROFILES_FILE = APP_DATA_DIR / "profiles.dat"
DEFAULT_EXPORT_FILE = APP_DATA_DIR / "profiles_export.json"


@dataclass(slots=True)
class Profile:
    name: str
    baseText: str
    secret: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Profile":
        name = str(data.get("name", "")).strip()
        base_text = str(data.get("baseText", ""))
        secret = str(data.get("secret", "")).strip()
        profile = cls(name=name, baseText=base_text, secret=secret)
        profile.validate()
        return profile

    def validate(self) -> None:
        if not self.name:
            raise ValueError("Profile name is required.")
        if not self.baseText:
            raise ValueError("Base text is required.")
        validate_secret(self.secret)


class ProfileManager:
    def __init__(self, path: Path = DEFAULT_PROFILES_FILE) -> None:
        self.path = path
        self.profiles: list[Profile] = []
        self.active_profile_name = ""
        self.auto_copy_on_launch = False
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._migrate_legacy_profiles()
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            self.profiles = []
            self.active_profile_name = ""
            self.auto_copy_on_launch = False
            self.save()
            return

        try:
            encrypted_data = self.path.read_bytes()
            _, decrypted_data = win32crypt.CryptUnprotectData(encrypted_data, None, None, None, 0)
            raw = json.loads(decrypted_data.decode("utf-8"))
        except Exception as exc:
            backup = self.path.with_suffix(".invalid.dat")
            shutil.copy2(self.path, backup)
            raise ValueError(f"{self.path.name} is invalid. Backup created at {backup}.") from exc

        if isinstance(raw, list):
            profile_items = raw
            settings = {}
        elif isinstance(raw, dict):
            profile_items = raw.get("profiles", [])
            settings = raw.get("settings", {})
        else:
            raise ValueError(f"{self.path.name} must contain a JSON object or array.")

        self.profiles = [Profile.from_dict(item) for item in profile_items if isinstance(item, dict)]
        self.active_profile_name = str(settings.get("activeProfile", "")).strip()
        self.auto_copy_on_launch = bool(settings.get("autoCopyOnLaunch", False))

        if self.profiles and self.active_profile_name not in self.names:
            self.active_profile_name = self.profiles[0].name
        if not self.profiles:
            self.active_profile_name = ""

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "settings": {
                "activeProfile": self.active_profile_name,
                "autoCopyOnLaunch": self.auto_copy_on_launch,
            },
            "profiles": [asdict(profile) for profile in self.profiles],
        }
        json_str = json.dumps(data, indent=2)
        encrypted_data = win32crypt.CryptProtectData(json_str.encode("utf-8"), "TOTP Profiles")
        self.path.write_bytes(encrypted_data)

    @property
    def names(self) -> list[str]:
        return [profile.name for profile in self.profiles]

    def get_active_profile(self) -> Profile | None:
        return self.get_profile(self.active_profile_name)

    def get_profile(self, name: str) -> Profile | None:
        return next((profile for profile in self.profiles if profile.name == name), None)

    def set_active_profile(self, name: str) -> None:
        if name and name not in self.names:
            raise ValueError("Profile does not exist.")
        self.active_profile_name = name
        self.save()

    def set_auto_copy_on_launch(self, enabled: bool) -> None:
        self.auto_copy_on_launch = enabled
        self.save()

    def add_profile(self, profile: Profile) -> None:
        self._upsert_profile(profile, original_name=None)

    def update_profile(self, original_name: str, profile: Profile) -> None:
        self._upsert_profile(profile, original_name=original_name)

    def delete_profile(self, name: str) -> None:
        self.profiles = [profile for profile in self.profiles if profile.name != name]
        if self.active_profile_name == name:
            self.active_profile_name = self.profiles[0].name if self.profiles else ""
        self.save()

    def export_profiles(self, export_path: Path = DEFAULT_EXPORT_FILE) -> Path:
        export_path.write_text(
            json.dumps({"profiles": [asdict(profile) for profile in self.profiles]}, indent=2),
            encoding="utf-8",
        )
        return export_path

    def import_profiles(self, import_path: Path) -> int:
        raw = json.loads(import_path.read_text(encoding="utf-8"))
        profile_items = raw.get("profiles", raw) if isinstance(raw, dict) else raw
        if not isinstance(profile_items, list):
            raise ValueError("Import file must contain a profile list.")

        imported = [Profile.from_dict(item) for item in profile_items if isinstance(item, dict)]
        for profile in imported:
            existing = self.get_profile(profile.name)
            if existing:
                existing.baseText = profile.baseText
                existing.secret = profile.secret
            else:
                self.profiles.append(profile)

        if self.profiles and not self.active_profile_name:
            self.active_profile_name = self.profiles[0].name
        self.save()
        return len(imported)

    def _upsert_profile(self, profile: Profile, original_name: str | None) -> None:
        profile.validate()
        duplicate = self.get_profile(profile.name)
        if duplicate and profile.name != original_name:
            raise ValueError("A profile with this name already exists.")

        if original_name:
            current = self.get_profile(original_name)
            if current is None:
                raise ValueError("Profile does not exist.")
            current.name = profile.name
            current.baseText = profile.baseText
            current.secret = profile.secret
            if self.active_profile_name == original_name:
                self.active_profile_name = profile.name
        else:
            self.profiles.append(profile)
            if not self.active_profile_name:
                self.active_profile_name = profile.name

        self.save()

    def _migrate_legacy_profiles(self) -> None:
        if self.path.exists():
            return

        candidates = [self.path.with_name("profiles.json"), APP_DIR / "profiles.json"]
        if getattr(sys, "frozen", False):
            candidates.insert(0, Path(sys.executable).resolve().parent / "profiles.json")

        for candidate in candidates:
            if candidate.exists() and candidate.resolve() != self.path.resolve():
                try:
                    json_str = candidate.read_text(encoding="utf-8")
                    json.loads(json_str)  # Verify it's valid JSON
                    encrypted_data = win32crypt.CryptProtectData(json_str.encode("utf-8"), "TOTP Profiles")
                    self.path.write_bytes(encrypted_data)
                    return
                except Exception:
                    continue
