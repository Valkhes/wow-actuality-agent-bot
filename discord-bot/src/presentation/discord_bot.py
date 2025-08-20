import discord
from discord.ext import commands
import structlog
import asyncio
from datetime import datetime
from typing import Optional

from ..domain.entities import WoWQuestion, BotUser
from ..application.use_cases import HandleWoWQuestionUseCase, RateLimitError, APIServiceError

logger = structlog.get_logger()


class WoWBot(commands.Bot):
    def __init__(
        self,
        command_prefix: str,
        intents: discord.Intents,
        question_use_case: HandleWoWQuestionUseCase,
        max_response_length: int = 2000
    ):
        super().__init__(command_prefix=command_prefix, intents=intents)
        self.question_use_case = question_use_case
        self.max_response_length = max_response_length

    async def setup_hook(self):
        try:
            synced = await self.tree.sync()
            logger.info("Synced commands", command_count=len(synced))
        except Exception as e:
            logger.error("Failed to sync commands", error=str(e), error_type=type(e).__name__)

    async def on_ready(self):
        logger.info(
            "Bot is ready",
            bot_name=self.user.name,
            bot_id=self.user.id,
            guild_count=len(self.guilds)
        )

    async def on_error(self, event, *args, **kwargs):
        logger.error(
            "Discord event error",
            event=event,
            args=args,
            kwargs=kwargs,
            exc_info=True
        )


class WoWCog(commands.Cog):
    def __init__(self, bot: WoWBot):
        self.bot = bot

    @discord.app_commands.command(
        name="ask",
        description="Ask a question about World of Warcraft news and updates"
    )
    async def ask_wow_question(
        self,
        interaction: discord.Interaction,
        question: str
    ):
        # Defer the response since API calls might take time
        await interaction.response.defer()
        
        try:
            # Create domain entities
            wow_question = WoWQuestion(
                content=question,
                user_id=str(interaction.user.id),
                username=interaction.user.display_name,
                channel_id=str(interaction.channel.id),
                guild_id=str(interaction.guild.id) if interaction.guild else None,
                timestamp=datetime.now()
            )
            
            bot_user = BotUser(
                id=str(interaction.user.id),
                username=interaction.user.name,
                discriminator=interaction.user.discriminator,
                avatar_url=str(interaction.user.display_avatar.url) if interaction.user.display_avatar else None
            )
            
            logger.info(
                "Processing ask command",
                user_id=bot_user.id,
                username=bot_user.username,
                question_length=len(question),
                guild_id=wow_question.guild_id
            )
            
            # Execute use case
            response = await self.bot.question_use_case.execute(wow_question, bot_user)
            
            # Format response
            response_text = response.content
            
            # Truncate if too long for Discord
            if len(response_text) > self.bot.max_response_length:
                response_text = response_text[:self.bot.max_response_length - 3] + "..."
            
            # Add source information if available
            if response.source_articles:
                footer_text = f"\n\n*Sources: {len(response.source_articles)} articles*"
                if len(response_text) + len(footer_text) <= self.bot.max_response_length:
                    response_text += footer_text
            
            await interaction.followup.send(response_text)
            
            logger.info(
                "Successfully responded to ask command",
                user_id=bot_user.id,
                response_length=len(response_text),
                source_count=len(response.source_articles or [])
            )
            
        except RateLimitError as e:
            await interaction.followup.send(
                "You're asking questions too quickly! Please wait a minute before asking another question.",
                ephemeral=True
            )
            logger.warning(
                "Rate limit hit",
                user_id=str(interaction.user.id),
                username=interaction.user.display_name
            )
            
        except APIServiceError as e:
            await interaction.followup.send(
                "I'm having trouble getting information right now. Please try again in a moment.",
                ephemeral=True
            )
            logger.error(
                "API service error",
                user_id=str(interaction.user.id),
                error=str(e)
            )
            
        except ValueError as e:
            await interaction.followup.send(
                f"Error: {str(e)}",
                ephemeral=True
            )
            logger.warning(
                "Invalid question",
                user_id=str(interaction.user.id),
                error=str(e)
            )
            
        except Exception as e:
            await interaction.followup.send(
                "An unexpected error occurred. Please try again later.",
                ephemeral=True
            )
            logger.error(
                "Unexpected error in ask command",
                user_id=str(interaction.user.id),
                error=str(e),
                exc_info=True
            )

    @discord.app_commands.command(
        name="help",
        description="Get help with using the WoW bot"
    )
    async def help_command(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🏰 WoW Actuality Bot Help",
            description="Ask questions about World of Warcraft news and updates!",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="📝 Commands",
            value="`/ask <question>` - Ask about WoW news and updates",
            inline=False
        )
        
        embed.add_field(
            name="⚡ Rate Limits",
            value="1 question per user per minute",
            inline=True
        )
        
        embed.add_field(
            name="📏 Question Length",
            value="Maximum 60 characters",
            inline=True
        )
        
        embed.add_field(
            name="Example",
            value="`/ask What are the latest changes in Season of Discovery?`",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: WoWBot):
    await bot.add_cog(WoWCog(bot))