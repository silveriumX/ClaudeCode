"""
UserBot для создания и управления чатами
Работает от аккаунта-администратора через Pyrogram
"""
import asyncio
import logging
from pyrogram import Client
from pyrogram.errors import FloodWait, BadRequest
from sheets import ChatSheetsManager
import config

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class ChatUserBot:
    """UserBot для управления чатами"""

    def __init__(self):
        """Инициализация UserBot"""
        self.app = Client(
            config.USERBOT_SESSION,
            api_id=config.USERBOT_API_ID,
            api_hash=config.USERBOT_API_HASH
        )
        self.sheets = ChatSheetsManager()
        self.is_running = False

    async def create_group_chat(self, title: str, description: str = '') -> dict:
        """
        Создать групповой чат

        Args:
            title: Название чата
            description: Описание чата

        Returns:
            dict с полями: chat_id, invite_link или error
        """
        try:
            # Создаем группу (basic group)
            chat = await self.app.create_group(title, [])

            logger.info(f"Created group chat: {title} (ID: {chat.id})")

            # Генерируем invite link
            invite_link = await self.app.export_chat_invite_link(chat.id)

            logger.info(f"Generated invite link for {title}: {invite_link}")

            # Если есть описание - устанавливаем
            if description:
                try:
                    await self.app.set_chat_description(chat.id, description)
                except Exception as e:
                    logger.warning(f"Failed to set description: {e}")

            return {
                'chat_id': chat.id,
                'invite_link': invite_link,
                'error': None
            }

        except FloodWait as e:
            logger.warning(f"FloodWait: need to wait {e.value} seconds")
            return {
                'chat_id': None,
                'invite_link': None,
                'error': f"Rate limit: wait {e.value}s"
            }

        except BadRequest as e:
            logger.error(f"BadRequest while creating chat: {e}")
            return {
                'chat_id': None,
                'invite_link': None,
                'error': f"Bad request: {str(e)}"
            }

        except Exception as e:
            logger.error(f"Error creating chat: {e}")
            return {
                'chat_id': None,
                'invite_link': None,
                'error': str(e)
            }

    async def process_pending_chats(self):
        """
        Обработать все pending запросы на создание чатов
        """
        try:
            pending = self.sheets.get_pending_chat_requests()

            if not pending:
                logger.debug("No pending chat requests")
                return

            logger.info(f"Found {len(pending)} pending chat requests")

            for request in pending:
                request_id = request['id']
                title = request['title']
                description = request.get('description', '')

                logger.info(f"Processing request {request_id}: {title}")

                # Создаем чат
                result = await self.create_group_chat(title, description)

                if result['error']:
                    # Ошибка при создании
                    logger.error(f"Failed to create chat {request_id}: {result['error']}")
                    self.sheets.update_chat_failed(request_id, result['error'])
                else:
                    # Успешно создан
                    chat_id = result['chat_id']
                    invite_link = result['invite_link']

                    logger.info(f"Chat {request_id} created successfully: {chat_id}")

                    # Обновляем Google Sheets
                    self.sheets.update_chat_created(request_id, chat_id, invite_link)

                    # Добавляем создателя как участника
                    creator_id = request.get('creator_id')
                    if creator_id:
                        self.sheets.add_participant(
                            chat_id,
                            creator_id,
                            config.CHAT_ROLE_CREATOR
                        )

                # Небольшая задержка между запросами
                await asyncio.sleep(2)

        except Exception as e:
            logger.error(f"Error processing pending chats: {e}")

    async def polling_loop(self):
        """
        Основной цикл проверки pending запросов
        """
        logger.info(f"Starting polling loop (interval: {config.CHAT_POLL_INTERVAL}s)")
        self.is_running = True

        while self.is_running:
            try:
                await self.process_pending_chats()
                await asyncio.sleep(config.CHAT_POLL_INTERVAL)
            except Exception as e:
                logger.error(f"Error in polling loop: {e}")
                await asyncio.sleep(config.CHAT_POLL_INTERVAL)

    async def run(self):
        """Запустить UserBot"""
        logger.info("Starting ChatManager UserBot...")

        async with self.app:
            # Проверяем авторизацию
            me = await self.app.get_me()
            logger.info(f"Logged in as: {me.first_name} (@{me.username}, ID: {me.id})")

            # Запускаем polling loop
            await self.polling_loop()

    def stop(self):
        """Остановить UserBot"""
        logger.info("Stopping UserBot...")
        self.is_running = False


async def main():
    """Главная функция"""
    userbot = ChatUserBot()

    try:
        await userbot.run()
    except KeyboardInterrupt:
        logger.info("Received KeyboardInterrupt, stopping...")
        userbot.stop()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise


if __name__ == '__main__':
    asyncio.run(main())
