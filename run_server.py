from src.server import start_server
import tkinter
from PIL import Image, ImageTk
from dotenv import load_dotenv
from src.utils import load_config

if __name__ == "__main__":
    host, port = load_config()
    start_server(host, port)