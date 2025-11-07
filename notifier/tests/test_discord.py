"""Tests for the Discord webhook client."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from notifier.config import NotificationConfig, NotificationType
from notifier.discord import DiscordClient, DiscordEmbed


class TestDiscordEmbed:
    """Test DiscordEmbed builder class."""

    def test_basic_embed(self):
        """Test creating a basic embed."""
        embed = DiscordEmbed(title="Test Title", description="Test Description", color=123456)

        data = embed.to_dict()
        assert data["title"] == "Test Title"
        assert data["description"] == "Test Description"
        assert data["color"] == 123456
        assert "timestamp" in data

    def test_add_field(self):
        """Test adding fields to embed."""
        embed = DiscordEmbed(title="Test")
        embed.add_field("Field 1", "Value 1", inline=True)
        embed.add_field("Field 2", "Value 2", inline=False)

        data = embed.to_dict()
        assert len(data["fields"]) == 2
        assert data["fields"][0]["name"] == "Field 1"
        assert data["fields"][0]["value"] == "Value 1"
        assert data["fields"][0]["inline"] is True
        assert data["fields"][1]["inline"] is False

    def test_set_thumbnail(self):
        """Test setting thumbnail."""
        embed = DiscordEmbed(title="Test")
        embed.set_thumbnail("https://example.com/image.png")

        data = embed.to_dict()
        assert data["thumbnail"]["url"] == "https://example.com/image.png"

    def test_set_footer(self):
        """Test setting footer."""
        embed = DiscordEmbed(title="Test")
        embed.set_footer("Footer text", icon_url="https://example.com/icon.png")

        data = embed.to_dict()
        assert data["footer"]["text"] == "Footer text"
        assert data["footer"]["icon_url"] == "https://example.com/icon.png"

    def test_set_author(self):
        """Test setting author."""
        embed = DiscordEmbed(title="Test")
        embed.set_author(
            "Author", url="https://example.com", icon_url="https://example.com/icon.png"
        )

        data = embed.to_dict()
        assert data["author"]["name"] == "Author"
        assert data["author"]["url"] == "https://example.com"
        assert data["author"]["icon_url"] == "https://example.com/icon.png"

    def test_method_chaining(self):
        """Test that methods support chaining."""
        embed = (
            DiscordEmbed(title="Test")
            .add_field("Field", "Value")
            .set_thumbnail("https://example.com/thumb.png")
            .set_footer("Footer")
        )

        data = embed.to_dict()
        assert "fields" in data
        assert "thumbnail" in data
        assert "footer" in data


class TestDiscordClient:
    """Test DiscordClient class."""

    @pytest.fixture
    def config(self):
        """Fixture to provide a test configuration."""
        config = MagicMock(spec=NotificationConfig)
        config.discord_webhook_url = "https://discord.com/api/webhooks/test"
        config.discord_username = "Test Bot"
        config.discord_avatar_url = None
        config.timeout_seconds = 5
        config.get_color.return_value = 3066993
        return config

    @pytest.fixture
    def client(self, config):
        """Fixture to provide a Discord client."""
        return DiscordClient(config)

    @pytest.mark.asyncio
    async def test_send_message_success(self, client):
        """Test successful message sending."""
        mock_response = AsyncMock()
        mock_response.status = 204

        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_post.return_value.__aenter__.return_value = mock_response

            result = await client.send_message(content="Test message")

            assert result is True
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_no_webhook(self):
        """Test sending message with no webhook configured."""
        config = MagicMock(spec=NotificationConfig)
        config.discord_webhook_url = None
        client = DiscordClient(config)

        result = await client.send_message(content="Test")
        assert result is False

    @pytest.mark.asyncio
    async def test_send_message_with_embeds(self, client):
        """Test sending message with embeds."""
        embed = DiscordEmbed(title="Test Embed")
        mock_response = AsyncMock()
        mock_response.status = 204

        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_post.return_value.__aenter__.return_value = mock_response

            result = await client.send_message(embeds=[embed])

            assert result is True
            # Verify embed was included in payload
            call_args = mock_post.call_args
            assert "embeds" in call_args.kwargs["json"]

    @pytest.mark.asyncio
    async def test_send_message_rate_limited(self, client):
        """Test handling Discord rate limit."""
        mock_response = AsyncMock()
        mock_response.status = 429
        mock_response.json.return_value = {"retry_after": 5}

        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_post.return_value.__aenter__.return_value = mock_response

            result = await client.send_message(content="Test")

            assert result is False

    @pytest.mark.asyncio
    async def test_send_message_error(self, client):
        """Test handling error response."""
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.text.return_value = "Internal Server Error"

        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_post.return_value.__aenter__.return_value = mock_response

            result = await client.send_message(content="Test")

            assert result is False

    @pytest.mark.asyncio
    async def test_send_message_timeout(self, client):
        """Test handling timeout."""
        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_post.side_effect = asyncio.TimeoutError()

            result = await client.send_message(content="Test")

            assert result is False

    @pytest.mark.asyncio
    async def test_send_notification(self, client):
        """Test send_notification helper method."""
        mock_response = AsyncMock()
        mock_response.status = 204

        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_post.return_value.__aenter__.return_value = mock_response

            result = await client.send_notification(
                NotificationType.INFO,
                "Test Title",
                description="Test Description",
                fields={"Field": "Value"},
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
        mock_response.status = 204

        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_post.return_value.__aenter__.return_value = mock_response

            await client.send_message(content="Test", username="Custom Bot")

            call_args = mock_post.call_args
            assert call_args.kwargs["json"]["username"] == "Custom Bot"

    @pytest.mark.asyncio
    async def test_avatar_url(self, client):
        """Test sending with avatar URL."""
        mock_response = AsyncMock()
        mock_response.status = 204

        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_post.return_value.__aenter__.return_value = mock_response

            await client.send_message(content="Test", avatar_url="https://example.com/avatar.png")

            call_args = mock_post.call_args
            assert call_args.kwargs["json"]["avatar_url"] == "https://example.com/avatar.png"
