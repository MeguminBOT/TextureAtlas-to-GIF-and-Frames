class ExceptionHandler:
    @staticmethod
    def handle_exception(e, metadata_path, sprites_failed):
        if "Coordinate '" in str(e) and "' is less than '" in str(e):
            sprites_failed += 1
            raise Exception(f"XML or TXT frame dimension data doesn't match the spritesheet dimensions.\n\nError: {str(e)}\n\nFile: {metadata_path}\n\nThis error can also occur from Alpha Threshold being set too high.")
        elif "'NoneType' object is not subscriptable" in str(e):
            sprites_failed += 1
            raise Exception(f"XML or TXT frame dimension data doesn't match the spritesheet dimensions.\n\nError: {str(e)}\n\nFile: {metadata_path}")
        else:
            sprites_failed += 1
            raise Exception(f"An error occurred: {str(e)}.\n\nFile:{metadata_path}")