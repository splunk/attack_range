from colorama import Fore, Back, Style, init
import datetime
init(autoreset=True)

class ColorPrint:
    """
    description: small Utility class for colored printing to the console. tested in macos terminal
    by. tccontre18 ~ Br3akp0int
    """


    @staticmethod
    def print_cyan_fg(msg:str)->None:
        print(Fore.CYAN + msg)
        return
    
    @staticmethod
    def print_red_fg(msg:str)->None:
        print(Fore.RED + msg)
        return

    @staticmethod
    def print_green_fg(msg:str)->None:
        print(Fore.GREEN + msg)
        return
    
    @staticmethod
    def print_yellow_fg(msg:str)->None:
        print(Fore.YELLOW + msg)
        return
    
    @staticmethod
    def print_blue_fg(msg:str)->None:
        print(Fore.BLUE + msg)
        return
    
    @staticmethod
    def print_magenta_fg(msg:str)->None:
        print(Fore.MAGENTA + msg)
        return
    
    @staticmethod
    def print_bold_style(msg:str)->None:
        print(Style.BRIGHT + msg)
        return  
    
    @staticmethod
    def print_dim_style(msg:str)->None:
        print(Style.DIM + msg)
        return
    
    @staticmethod
    def print_normal_style(msg:str)->None:
        print(Style.NORMAL + msg)
        return
    
    @staticmethod
    def print_info_fg(msg:str)->None:
        timestamp = f"[ {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} ]"
        print(Fore.MAGENTA + " "* 3 + timestamp+ "==> " + Style.RESET_ALL + Fore.CYAN  + msg)
        return
    
    @staticmethod
    def print_warning_fg(msg:str)->None:
        timestamp = f"[ {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} ]"
        print(Fore.MAGENTA + " "* 3 + timestamp+ "==> " + Style.RESET_ALL + Fore.YELLOW  + msg)
        return
    
    @staticmethod
    def print_error_fg(msg:str)->None:
        timestamp = f"[ {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} ]"
        print(Fore.MAGENTA +  " "* 3 + timestamp+ "==> " + Style.RESET_ALL + Fore.RED + msg)
        return 
    
    @staticmethod
    def print_success_fg(msg:str)->None:
        timestamp = f"[ {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} ]"
        print(Fore.MAGENTA +  " "* 3 + timestamp+ "==> " + Style.RESET_ALL + Fore.LIGHTGREEN_EX + msg)
        return