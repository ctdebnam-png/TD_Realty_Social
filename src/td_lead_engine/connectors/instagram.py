"""Instagram data export connector."""

import json
import zipfile
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from .base import BaseConnector, ImportResult, RawLead


class InstagramConnector(BaseConnector):
    """Import leads from Instagram data export (Download Your Data feature)."""

    source_name = "instagram"

    def import_from_path(self, path: Path) -> ImportResult:
        """Import from Instagram export zip or extracted folder."""
        result = ImportResult(source=self.source_name)

        error = self.validate_path(path)
        if error:
            result.add_error(error)
            return result

        try:
            if path.suffix == ".zip":
                return self._import_from_zip(path)
            elif path.is_dir():
                return self._import_from_folder(path)
            else:
                result.add_error(f"Expected .zip file or directory, got: {path}")
                return result
        except Exception as e:
            result.add_error(f"Import failed: {str(e)}")
            return result

    def _import_from_zip(self, zip_path: Path) -> ImportResult:
        """Import from a zip file."""
        result = ImportResult(source=self.source_name)

        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                # Look for key files in the export
                file_list = zf.namelist()

                # Import followers
                followers_data = self._read_json_from_zip(
                    zf, file_list,
                    ["followers_and_following/followers_1.json", "followers.json"]
                )
                if followers_data:
                    for follower in self._parse_followers(followers_data):
                        result.leads.append(follower)

                # Import messages/conversations
                messages_data = self._find_message_files(zf, file_list)
                for msg_data in messages_data:
                    leads = self._parse_messages(msg_data)
                    for lead in leads:
                        result.leads.append(lead)

                # Import commenters
                comments_data = self._read_json_from_zip(
                    zf, file_list,
                    ["comments/post_comments_1.json", "comments.json"]
                )
                if comments_data:
                    for commenter in self._parse_comments(comments_data):
                        result.leads.append(commenter)

        except zipfile.BadZipFile:
            result.add_error(f"Invalid zip file: {zip_path}")
        except Exception as e:
            result.add_error(f"Error reading zip: {str(e)}")

        return result

    def _import_from_folder(self, folder_path: Path) -> ImportResult:
        """Import from an extracted folder."""
        result = ImportResult(source=self.source_name)

        # Import followers
        followers_paths = [
            folder_path / "followers_and_following" / "followers_1.json",
            folder_path / "followers.json",
        ]
        for fp in followers_paths:
            if fp.exists():
                try:
                    with open(fp, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    for follower in self._parse_followers(data):
                        result.leads.append(follower)
                    break
                except Exception as e:
                    result.add_warning(f"Error reading {fp}: {e}")

        # Import messages
        messages_dir = folder_path / "messages" / "inbox"
        if messages_dir.exists():
            for conv_dir in messages_dir.iterdir():
                if conv_dir.is_dir():
                    msg_file = conv_dir / "message_1.json"
                    if msg_file.exists():
                        try:
                            with open(msg_file, 'r', encoding='utf-8') as f:
                                msg_data = json.load(f)
                            for lead in self._parse_messages(msg_data):
                                result.leads.append(lead)
                        except Exception as e:
                            result.add_warning(f"Error reading {msg_file}: {e}")

        # Import comments
        comments_paths = [
            folder_path / "comments" / "post_comments_1.json",
            folder_path / "comments.json",
        ]
        for cp in comments_paths:
            if cp.exists():
                try:
                    with open(cp, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    for commenter in self._parse_comments(data):
                        result.leads.append(commenter)
                    break
                except Exception as e:
                    result.add_warning(f"Error reading {cp}: {e}")

        if not result.leads:
            result.add_warning("No leads found in Instagram export")

        return result

    def _read_json_from_zip(
        self,
        zf: zipfile.ZipFile,
        file_list: List[str],
        possible_paths: List[str]
    ) -> Optional[Any]:
        """Try to read JSON from multiple possible paths in zip."""
        for path in possible_paths:
            matching = [f for f in file_list if f.endswith(path) or path in f]
            if matching:
                try:
                    with zf.open(matching[0]) as f:
                        return json.load(f)
                except Exception:
                    continue
        return None

    def _find_message_files(
        self,
        zf: zipfile.ZipFile,
        file_list: List[str]
    ) -> List[Dict[str, Any]]:
        """Find and read all message JSON files."""
        messages = []
        msg_files = [f for f in file_list if "message" in f.lower() and f.endswith(".json")]
        for msg_file in msg_files:
            try:
                with zf.open(msg_file) as f:
                    data = json.load(f)
                    if isinstance(data, dict) and "messages" in data:
                        messages.append(data)
            except Exception:
                continue
        return messages

    def _parse_followers(self, data: Any) -> List[RawLead]:
        """Parse followers data."""
        leads = []

        # Handle different Instagram export formats
        followers_list = []
        if isinstance(data, list):
            followers_list = data
        elif isinstance(data, dict):
            if "relationships_followers" in data:
                followers_list = data["relationships_followers"]
            elif "followers" in data:
                followers_list = data["followers"]

        for follower in followers_list:
            try:
                username = None
                if isinstance(follower, dict):
                    # New format
                    if "string_list_data" in follower:
                        sld = follower["string_list_data"]
                        if sld and len(sld) > 0:
                            username = sld[0].get("value")
                    # Old format
                    elif "username" in follower:
                        username = follower["username"]
                    elif "value" in follower:
                        username = follower["value"]

                if username:
                    leads.append(RawLead(
                        source="instagram",
                        username=username,
                        profile_url=f"https://instagram.com/{username}",
                        raw_data=follower if isinstance(follower, dict) else {"username": username}
                    ))
            except Exception:
                continue

        return leads

    def _parse_messages(self, data: Dict[str, Any]) -> List[RawLead]:
        """Parse messages/DM conversations."""
        leads = []

        participants = data.get("participants", [])
        messages = data.get("messages", [])

        # Get other participants (not you)
        for participant in participants:
            name = participant.get("name", "")
            if not name:
                continue

            # Collect their messages
            their_messages = []
            for msg in messages:
                sender = msg.get("sender_name", "")
                content = msg.get("content", "")
                if sender == name and content:
                    # Decode Instagram's encoding
                    try:
                        content = content.encode('latin1').decode('utf-8')
                    except Exception:
                        pass
                    their_messages.append(content)

            leads.append(RawLead(
                source="instagram",
                name=name,
                username=name.lower().replace(" ", ""),
                messages=their_messages[:50],  # Limit to last 50
                profile_url=f"https://instagram.com/{name.lower().replace(' ', '')}",
                raw_data={"participant": participant, "message_count": len(their_messages)}
            ))

        return leads

    def _parse_comments(self, data: Any) -> List[RawLead]:
        """Parse comments on your posts."""
        leads = []
        seen_usernames = set()

        # Handle different formats
        comments_list = []
        if isinstance(data, list):
            comments_list = data
        elif isinstance(data, dict):
            comments_list = data.get("comments_media_comments", [])

        for comment in comments_list:
            try:
                username = None
                comment_text = ""

                if isinstance(comment, dict):
                    # New format
                    if "string_list_data" in comment:
                        sld = comment["string_list_data"]
                        if sld:
                            username = sld[0].get("value", "").split(" ")[0]
                            comment_text = sld[0].get("value", "")
                    # Legacy format
                    elif "author" in comment:
                        username = comment["author"]
                        comment_text = comment.get("text", "")

                if username and username not in seen_usernames:
                    seen_usernames.add(username)
                    leads.append(RawLead(
                        source="instagram",
                        username=username,
                        comments=[comment_text] if comment_text else [],
                        profile_url=f"https://instagram.com/{username}",
                        raw_data=comment
                    ))
            except Exception:
                continue

        return leads
