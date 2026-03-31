import os
import re
import asyncio
import logging
import aiohttp
from typing import Dict, List, Optional
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from google.cloud import secretmanager

# Load configuration
load_dotenv()
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
API_BACKEND_URL = os.environ.get("API_BACKEND_URL", "http://localhost:8000/api/v1/scan")
DEBUG_MODE = os.environ.get("DEBUG_MODE", "false").lower() == "true"

def get_api_key_from_secret_manager():
    project_id = os.environ.get("PROJECT_ID", "virustotal-lab")
    secret_id = "MATA_API_KEY"
    
    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        logging.getLogger(__name__).error(f"❌ Failed to fetch secret from Secret Manager: {e}")
        return None

MATA_API_KEY = os.environ.get("MATA_API_KEY") or get_api_key_from_secret_manager()

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

class ResponseFormatter:
    RESPONSE_TEMPLATES = {
        "DANGER":  {"emoji": "🚨", "level": "DANGER: Malicious link detected!",  "rec": "🚫 DO NOT VISIT - This website poses a significant security risk."},
        "WARNING": {"emoji": "⚠️", "level": "WARNING: Potentially malicious link detected!", "rec": "⚠️ SUSPICIOUS - Proceed with caution and only if you trust the sender."},
        "SAFE":    {"emoji": "✅", "level": "Link seems safe",    "rec": "✅ SAFE - No threats detected, but always be cautious with unknown websites."},
        "ERROR":   {"emoji": "❓", "level": "ERROR",   "rec": "❓ INCONCLUSIVE - Exercise caution as threat assessment is unclear."}
    }

    def _get_risk_level(self, vt_result: dict, wr_result: dict, ai_result: dict) -> str:
        if vt_result.get("error") or wr_result.get("error"):
            return "ERROR"
        
        vt_factors = vt_result.get("risk_factors", {})
        wr_factors = wr_result.get("risk_factors", {})
        ai_factors = ai_result.get("risk_factors", {})

        if (vt_factors.get("gti_verdict") == "VERDICT_MALICIOUS" or 
            (vt_factors.get("gti_score") is not None and vt_factors.get("gti_score") >= 60) or 
            wr_factors.get("has_high_threat") or 
            ai_factors.get("ai_risk") == "high"):
            return "DANGER"

        if (vt_factors.get("gti_verdict") == "VERDICT_HARMLESS" or 
            (vt_factors.get("classic_score") == 0 and wr_factors.get("is_clean"))):
            return "SAFE"
            
        return "WARNING"

    def format_combined_response(self, target: str, results_map: dict) -> str:
        
        vt_result = results_map.get("VirusTotal", {"error": True, "summary": "Not run", "risk_factors": {}})
        wr_result = results_map.get("Google Web Risk", {"error": True, "summary": "Not run", "risk_factors": {}})
        ai_result = results_map.get("AI Analysis", {"error": True, "summary": "Not run", "risk_factors": {}})

        risk_level = self._get_risk_level(vt_result, wr_result, ai_result)
        template = self.RESPONSE_TEMPLATES[risk_level]

        header = f"{template['emoji']} {template['level']}"
        recommendation = f"<b>Recommendation:</b>\n {template['rec']}"
        defanged_target = target.replace('.', '[.]').replace(':', '[:]')

        details_lines = []
        details_lines.append(f"VirusTotal: {vt_result.get('summary')}")
        details_lines.append(f"Google Web Risk: {wr_result.get('summary')}")
        details_lines.append(f"AI Analysis: {ai_result.get('summary')}")

        details_section = "\n".join(filter(None, details_lines))

        response = (
            f"{header}\n"
            f"Link: <code>{defanged_target}</code>\n"
            f"----------------------------------\n"
            f"{details_section}\n\n"
            f"{recommendation}"
        )
        return response


class TelegramBot:
    def __init__(self, token: str):
        self.application = Application.builder().token(token).build()
        self.response_formatter = ResponseFormatter()
        self._add_handlers()

    def _add_handlers(self):
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_html("Hi! I'm the Mata-Mata bot. Send me a message with a link to check it.")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = (
            "I check links against <b>VirusTotal</b>, <b>Google TI</b> and <b>Google Web Risk</b>.\n"
            "I use AI to analyse the website for any visual discrepencies, as well as to analyse the source code for signs of phishing.\n\n"
        )
        await update.message.reply_html(help_text)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message or not update.message.text: return
        text = update.message.text
        
        proc_msg = await update.message.reply_html(f"🔍 Sending `{text}` to the Mata-Mata backend...")
        
        if not MATA_API_KEY:
            await proc_msg.edit_text("❌ <b>Error</b>: MATA_API_KEY is not configured.", parse_mode='HTML')
            return

        headers = {"x-api-key": MATA_API_KEY}
        
        try:
            async with aiohttp.ClientSession() as session:
                # 1. Submit the scan request
                async with session.post(API_BACKEND_URL, json={"url": text}, headers=headers) as resp:
                    if resp.status != 200:
                        error_msg = await resp.text()
                        await proc_msg.edit_text(f"❌ <b>API Error {resp.status}</b>: {error_msg}", parse_mode='HTML')
                        return
                    
                    data = await resp.json()
                    job_id = data.get("job_id")
                    
                    if not job_id:
                        await proc_msg.edit_text("❌ <b>Error</b>: Did not receive job_id from backend.", parse_mode='HTML')
                        return
                
                # 2. Polling loop
                await proc_msg.edit_text(f"🔍 Scan job created. Polling for results...", parse_mode='HTML')
                
                status_url = f"{API_BACKEND_URL.replace('/scan', '/scan/status')}/{job_id}"
                
                attempts = 0
                max_time = 60
                start_time = asyncio.get_running_loop().time()
                
                while (asyncio.get_running_loop().time() - start_time) < max_time:
                    attempts += 1
                    
                    # Polling schedule: 2s for first 10 tries, then 5s
                    delay = 2 if attempts <= 10 else 5
                    await asyncio.sleep(delay)
                    
                    async with session.get(status_url) as status_resp:
                        if status_resp.status == 200:
                            status_data = await status_resp.json()
                            status = status_data.get("status")
                            
                            if status == "completed":
                                final_response = self.response_formatter.format_combined_response(
                                    status_data.get("url", text), 
                                    status_data.get("results", {})
                                )
                                await proc_msg.edit_text(final_response, parse_mode='HTML')
                                return
                            elif status == "failed":
                                error_msg = status_data.get("error", "Unknown error")
                                await proc_msg.edit_text(f"❌ <b>Scan Failed</b>: {error_msg}", parse_mode='HTML')
                                return
                            else:
                                # Still in progress
                                await proc_msg.edit_text(f"🔍 Still analyzing... (Attempt {attempts})", parse_mode='HTML')
                        else:
                            # HTTP error on status check
                            await proc_msg.edit_text(f"⚠️ Warning: Status check failed (HTTP {status_resp.status}). Retrying...", parse_mode='HTML')
                
                # Timeout reached
                await proc_msg.edit_text(f"⏰ <b>Timeout</b>: Scan taking longer than {max_time} seconds. Please check later.", parse_mode='HTML')
                
                        
        except Exception as e:
            logger.error(f"Error calling backend API: {e}", exc_info=True)
            await proc_msg.edit_text(f"❌ <b>Connection Error</b>: Could not reach backend API at {API_BACKEND_URL}.", parse_mode='HTML')

    def run(self):
        self.application.run_polling()

if __name__ == "__main__":
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN is missing in environment.")
        exit(1)
    
    bot = TelegramBot(TELEGRAM_TOKEN)
    logger.info("Starting Telegram Bot Poller...")
    bot.run()
