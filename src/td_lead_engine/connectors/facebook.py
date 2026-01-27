"""Facebook data export connector."""

import json
import zipfile
from pathlib import Path
from typing import Optional, Dict, Any, List

from .base import BaseConnector, ImportResult, RawLead


class FacebookConnector(BaseConnector):
    """Import leads from Facebook data export (Download Your Information feature)."""

    source_name = "facebook"

    def import_from_path(self, path: Path) -> ImportResult:
        """Import from Facebook export zip or extracted folder."""
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
                file_list = zf.namelist()

                # Import friends list
                friends_data = self._read_json_from_zip(
                    zf, file_list,
                    ["friends/friends.json", "friends_and_followers/friends.json"]
                )
                if friends_data:
                    for friend in self._parse_friends(friends_data):
                        result.leads.append(friend)

                # Import followers
                followers_data = self._read_json_from_zip(
                    zf, file_list,
                    ["followers_and_following/followers.json", "followers.json"]
                )
                if followers_data:
                    for follower in self._parse_followers(followers_data):
                        result.leads.append(follower)

                # Import messages
                messages_data = self._find_message_files(zf, file_list)
                for msg_data in messages_data:
                    leads = self._parse_messages(msg_data)
                    for lead in leads:
                        result.leads.append(lead)

                # Import comments on your posts
                comments_data = self._read_json_from_zip(
                    zf, file_list,
                    ["comments_and_reactions/comments.json", "comments/comments.json"]
                )
                if comments_data:
                    for commenter in self._parse_comments(comments_data):
                        result.leads.append(commenter)

                # Import page/business followers if applicable
                page_followers = self._read_json_from_zip(
                    zf, file_list,
                    ["pages/followers.json", "your_pages/followers.json"]
                )
                if page_followers:
                    for follower in self._parse_page_followers(page_followers):
                        result.leads.append(follower)

        except zipfile.BadZipFile:
            result.add_error(f"Invalid zip file: {zip_path}")
        except Exception as e:
            result.add_error(f"Error reading zip: {str(e)}")

        return result

    def _import_from_folder(self, folder_path: Path) -> ImportResult:
        """Import from an extracted folder."""
        result = ImportResult(source=self.source_name)

        # Import friends
        friends_paths = [
            folder_path / "friends" / "friends.json",
            folder_path / "friends_and_followers" / "friends.json",
        ]
        for fp in friends_paths:
            if fp.exists():
                try:
                    with open(fp, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    for friend in self._parse_friends(data):
                        result.leads.append(friend)
                    break
                except Exception as e:
                    result.add_warning(f"Error reading {fp}: {e}")

        # Import followers
        followers_paths = [
            folder_path / "followers_and_following" / "followers.json",
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
        if not messages_dir.exists():
            messages_dir = folder_path / "messages"

        if messages_dir.exists():
            for item in messages_dir.iterdir():
                if item.is_dir():
                    msg_file = item / "message_1.json"
                    if msg_file.exists():
                        try:
                            with open(msg_file, 'r', encoding='utf-8') as f:
                                msg_data = json.load(f)
                            for lead in self._parse_messages(msg_data):
                                result.leads.append(lead)
                        except Exception as e:
                            result.add_warning(f"Error reading {msg_file}: {e}")

        if not result.leads:
            result.add_warning("No leads found in Facebook export")

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
        msg_files = [
            f for f in file_list
            if "message" in f.lower() and f.endswith(".json") and "inbox" in f.lower()
        ]
        for msg_file in msg_files:
            try:
                with zf.open(msg_file) as f:
                    data = json.load(f)
                    if isinstance(data, dict) and "messages" in data:
                        messages.append(data)
            except Exception:
                continue
        return messages

    def _decode_facebook_text(self, text: str) -> str:
        """Decode Facebook's escaped encoding."""
        if not text:
            return ""
        try:
            return text.encode('latin1').decode('utf-8')
        except Exception:
            return text

    def _parse_friends(self, data: Any) -> List[RawLead]:
        """Parse friends list data."""
        leads = []

        friends_list = []
        if isinstance(data, list):
            friends_list = data
        elif isinstance(data, dict):
            friends_list = data.get("friends_v2", data.get("friends", []))

        for friend in friends_list:
            try:
                name = None
                if isinstance(friend, dict):
                    name = friend.get("name")
                    if not name and "contact_info" in friend:
                        name = friend["contact_info"].get("name")

                if name:
                    name = self._decode_facebook_text(name)
                    leads.append(RawLead(
                        source="facebook",
                        name=name,
                        profile_url=friend.get("profile_uri"),
                        raw_data=friend
                    ))
            except Exception:
                continue

        return leads

    def _parse_followers(self, data: Any) -> List[RawLead]:
        """Parse followers data."""
        leads = []

        followers_list = []
        if isinstance(data, list):
            followers_list = data
        elif isinstance(data, dict):
            followers_list = data.get("followers_v2", data.get("followers", []))

        for follower in followers_list:
            try:
                name = None
                if isinstance(follower, dict):
                    name = follower.get("name")

                if name:
                    name = self._decode_facebook_text(name)
                    leads.append(RawLead(
                        source="facebook",
                        name=name,
                        raw_data=follower
                    ))
            except Exception:
                continue

        return leads

    def _parse_messages(self, data: Dict[str, Any]) -> List[RawLead]:
        """Parse Messenger conversations."""
        leads = []

        participants = data.get("participants", [])
        messages = data.get("messages", [])
        thread_type = data.get("thread_type", "")

        # Skip group chats for lead gen
        if thread_type == "RegularGroup" or len(participants) > 2:
            return leads

        for participant in participants:
            name = participant.get("name", "")
            if not name:
                continue

            name = self._decode_facebook_text(name)

            # Collect their messages
            their_messages = []
            for msg in messages:
                sender = msg.get("sender_name", "")
                content = msg.get("content", "")
                if self._decode_facebook_text(sender) == name and content:
                    content = self._decode_facebook_text(content)
                    their_messages.append(content)

            leads.append(RawLead(
                source="facebook",
                name=name,
                messages=their_messages[:50],  # Limit messages
                raw_data={"participant": participant, "message_count": len(their_messages)}
            ))

        return leads

    def _parse_comments(self, data: Any) -> List[RawLead]:
        """Parse comments on your posts/content."""
        leads = []
        seen_names = set()

        comments_list = []
        if isinstance(data, list):
            comments_list = data
        elif isinstance(data, dict):
            comments_list = data.get("comments_v2", data.get("comments", []))

        for comment in comments_list:
            try:
                author = None
                comment_text = ""

                if isinstance(comment, dict):
                    author = comment.get("author")
                    if "data" in comment:
                        for item in comment["data"]:
                            if "comment" in item:
                                comment_text = item["comment"].get("comment", "")

                if author:
                    author = self._decode_facebook_text(author)
                    if author not in seen_names:
                        seen_names.add(author)
                        leads.append(RawLead(
                            source="facebook",
                            name=author,
                            comments=[self._decode_facebook_text(comment_text)] if comment_text else [],
                            raw_data=comment
                        ))
            except Exception:
                continue

        return leads

    def _parse_page_followers(self, data: Any) -> List[RawLead]:
        """Parse business page followers."""
        leads = []

        followers_list = []
        if isinstance(data, list):
            followers_list = data
        elif isinstance(data, dict):
            followers_list = data.get("page_followers", data.get("followers", []))

        for follower in followers_list:
            try:
                name = None
                if isinstance(follower, dict):
                    name = follower.get("name")

                if name:
                    name = self._decode_facebook_text(name)
                    leads.append(RawLead(
                        source="facebook",
                        name=name,
                        notes="Page follower",
                        raw_data=follower
                    ))
            except Exception:
                continue

        return leads
