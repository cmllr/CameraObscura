
from time import strftime
from core import config, logging
import re
from os.path import join
from os import listdir, unlink
import psutil

def replace_placeholders(text: str) -> str:
    """
    Replace placeholders from the given text.

    Placeholders are hereby two set of replacements:
        - strftime() format placeholders for date and time - These are prefixed with a % symbol
        - placeholders of this project - These are prefixed with a $ symbol and represent configuration.cfg values. Therefore they follow the format $section.setting

    parameters:
        text: The text containing the Python date time variables, see the params fro strftime() for details

    returns:
        A string with the replaced values
        If the text is none an empty string is returned
    """
    if text is None:
        return ""
    # first go: Replace date and time placeholders.
    text = strftime(text)
    # second go: Replace internal placeholders
    placeholder_matches = re.findall(r"(\$[a-z\.]+)", text)
    if placeholder_matches is not None:
        for match in placeholder_matches:
            name = match.replace("$", "")

            # Format must be $honeypot.setting_name
            if "." in name:
                parts = name.split(".")
                value = config.get_configuration_value(parts[0], parts[1])
                if type(value) == str:
                    text = text.replace(match, value)
    return text


def cleanup():
    """
    Search for lock files and other temporary files to delete it

    For lock files, the contained PID will be attemped to be killed
    """
    lock_folder = join(config.ROOT, "ul")

    files = listdir(lock_folder)
    for file in files:
        full_path = join(lock_folder, file)
        if full_path.endswith(".lock"):
            with open(full_path, "r") as file:
                pid = int(file.read())
                try:    
                    p = psutil.Process(pid)
                    if p.is_running():
                        p.kill()    
                    logging.log_wrapper(logging.EVENT_ID_REMOVED_LOCK, f"Found old lockfile {full_path} and killed PID {pid}", None, False)
                except psutil.NoSuchProcess:
                    pass
                unlink(full_path)
        
        if full_path.endswith(".ts") or full_path.endswith(".tmp"):
            unlink(full_path)