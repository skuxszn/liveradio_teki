"""Tests for the Slack webhook client."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from notifier.config import NotificationConfig, NotificationType
from notifier.slack import SlackAttachment, SlackClient


class TestSlackAttachment:
    """Test SlackAttachment builder class."""

    def test_basic_attachment(self):
        """Test creating a basic attachment."""
        attachment = SlackAttachment(
            title="Test Title", text="Test Text", color="good", fallback="Fallback"
        )

        data = attachment.to_dict()
        assert data["title"] == "Test Title"
        assert data["text"] == "Test Text"
        assert data["color"] == "good"
        assert data["fallback"] == "Fallback"

    def test_default_fallback(self):
        """Test that fallback defaults to title."""
        attachment = SlackAttachment(title="Test Title")

        data = attachment.to_dict()
        assert data["fallback"] == "Test Title"

    def test_add_field(self):
        """Test adding fields to attachment."""
        attachment = SlackAttachment(title="Test")
        attachment.add_field("Field 1", "Value 1", short=True)
        attachment.add_field("Field 2", "Value 2", short=False)

        data = attachment.to_dict()
        assert len(data["fields"]) == 2
        assert data["fields"][0]["title"] == "Field 1"
        assert data["fields"][0]["value"] == "Value 1"
        assert data["fields"][0]["short"] is True
        assert data["fields"][1]["short"] is False

    def test_set_footer(self):
        """Test setting footer."""
        attachment = SlackAttachment(title="Test")
        attachment.set_footer("Footer text", icon="https://example.com/icon.png")

        data = attachment.to_dict()
        assert data["footer"] == "Footer text"
        assert data["footer_icon"] == "https://example.com/icon.png"

    def test_set_timestamp(self):
        """Test setting timestamp."""
        attachment = SlackAttachment(title="Test")
        attachment.set_timestamp(1234567890)

        data = attachment.to_dict()
        assert data["ts"] == 1234567890

    def test_set_thumbnail(self):
        """Test setting thumbnail."""
        attachment = SlackAttachment(title="Test")
        attachment.set_thumbnail("https://example.com/thumb.png")

        data = attachment.to_dict()
        assert data["thumb_url"] == "https://example.com/thumb.png"

    def test_method_chaining(self):
        """Test that methods support chaining."""
        attachment = (
            SlackAttachment(title="Test")
            .add_field("Field", "Value")
            .set_thumbnail("https://example.com/thumb.png")
            .set_footer("Footer")
        )

        data = attachment.to_dict()
        assert "fields" in data
        assert "thumb_url" in data
        assert "footer" in data


class TestSlackClient:
    """Test SlackClient class."""

    @pytest.fixture
    def config(self):
        """Fixture to provide a test configuration."""
        config = MagicMock(spec=NotificationConfig)
        config.slack_webhook_url = "https://hooks.slack.com/services/test"
        config.slack_username = "Test Bot"
        config.slack_icon_emoji = ":robot:"
        config.timeout_seconds = 5
        return config

    @pytest.fixture
    def client(self, config):
        """Fixture to provide a Slack client."""
        return SlackClient(config)

    @pytest.mark.asyncio
    async def test_send_message_success(self, client):
        """Test successful message sending."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text.return_value = "ok"

        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_post.return_value.__aenter__.return_value = mock_response

            result = await client.send_message(text="Test message")

            assert result is True
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_no_webhook(self):
        """Test sending message with no webhook configured."""
        config = MagicMock(spec=NotificationConfig)
        config.slack_webhook_url = None
        client = SlackClient(config)

        result = await client.send_message(text="Test")
        assert result is False

    @pytest.mark.asyncio
    async def test_send_message_with_attachments(self, client):
        """Test sending message with attachments."""
        attachment = SlackAttachment(title="Test Attachment")
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text.return_value = "ok"

        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_post.return_value.__aenter__.return_value = mock_response

            result = await client.send_message(attachments=[attachment])

            assert result is True
            # Verify attachment was included in payload
            call_args = mock_post.call_args
            assert "attachments" in call_args.kwargs["json"]

    @pytest.mark.asyncio
    async def test_send_message_error(self, client):
        """Test handling error response."""
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.text.return_value = "error"

        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_post.return_value.__aenter__.return_value = mock_response

            result = await client.send_message(text="Test")

            assert result is False

    @pytest.mark.asyncio
    async def test_send_message_timeout(self, client):
        """Test handling timeout."""
        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_post.side_effect = asyncio.TimeoutError()

            result = await client.send_message(text="Test")

            assert result is False

    @pytest.mark.asyncio
    async def test_send_notification(self, client):
        """Test send_notification helper method."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text.return_value = "ok"

        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_post.return_value.__aenter__.return_value = mock_response

            result = await client.send_notification(
                NotificationType.INFO, "Test Title", text="Test Text", fields={"Field": "Value"}
            )

            assert result is True

    def test_send_sync(self, client):
        """Test synchronous send wrapper."""
        with patch.object(client, "send_notification", new=AsyncMock(return_value=True)):
            result = client.send_sync(NotificationType.INFO, "Test")
            assert result is True

    @pytest.mark.asyncio
    async def test_custom_username(self, client):
        """Test sending with custom username."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text.return_value = "ok"

        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_post.return_value.__aenter__.return_value = mock_response

            await client.send_message(text="Test", username="Custom Bot")

            call_args = mock_post.call_args
            assert call_args.kwargs["json"]["username"] == "Custom Bot"

    @pytest.mark.asyncio
    async def test_icon_emoji(self, client):
        """Test sending with icon emoji."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text.return_value = "ok"

        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_post.return_value.__aenter__.return_value = mock_response

            await client.send_message(text="Test", icon_emoji=":tada:")

            call_args = mock_post.call_args
            assert call_args.kwargs["json"]["icon_emoji"] == ":tada:"

    def test_color_mapping(self, client):
        """Test that notification types map to correct colors."""
        assert client.COLOR_MAP[NotificationType.TRACK_CHANGE] == "good"
        assert client.COLOR_MAP[NotificationType.ERROR] == "danger"
        assert client.COLOR_MAP[NotificationType.WARNING] == "warning"
        assert NotificationType.INFO in client.COLOR_MAP
        assert NotificationType.DAILY_SUMMARY in client.COLOR_MAP

    @pytest.mark.asyncio
    async def test_notification_with_thumbnail(self, client):
        """Test notification with thumbnail URL."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text.return_value = "ok"

        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_post.return_value.__aenter__.return_value = mock_response

            result = await client.send_notification(
                NotificationType.INFO,
                "Test Title",
                thumbnail_url="https://example.com/thumb.png",
            )

            assert result is True
            call_args = mock_post.call_args
            attachments = call_args.kwargs["json"]["attachments"]
            assert attachments[0]["thumb_url"] == "https://example.com/thumb.png"
