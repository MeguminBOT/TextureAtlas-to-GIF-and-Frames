import concurrent.futures
import os
import re
import requests
import sys
import webbrowser
import xml.etree.ElementTree as ET

from PIL import Image
import tkinter as tk
from tkinter import filedialog, ttk, messagebox

##### Update Checking #####
def check_for_updates(current_version):
    try:
        # Check the version number from the github repository.
        response = requests.get('https://raw.githubusercontent.com/MeguminBOT/TextureAtlas-to-GIF-and-Frames/main/latestVersion.txt')
        
        # Extract the version number from the github repository.
        latest_version = response.text.strip()

        # If the latest version is greater than the current version
        if latest_version > current_version:
            # Create a new Tkinter window and immediately hide it
            root = tk.Tk()
            root.withdraw()
            
            # Show a dialog asking the user if they want to download the update
            result = messagebox.askyesno("Update available", "An update is available. Do you want to download it now?")
            
            # If the user chose to download the update
            if result:
                print("User chose to download the update.")
                
                # Open the URL where the latest release can be downloaded
                webbrowser.open('https://github.com/MeguminBOT/TextureAtlas-to-GIF-and-Frames/releases/latest')
                
                # Exit the program
                sys.exit()
            else:
                print("User chose not to download the update.")
            
            # Destroy the Tkinter window and continue as normal.
            root.destroy()
        else:
            print("You are using the latest version of the application.")
    except requests.exceptions.RequestException as err:
        print("No internet connection or something went wrong, could not check for updates.")
        print("Error details:", err)

# Set the current version
current_version = '1.6.0'

# Call the function to check for updates
check_for_updates(current_version)

##### File processing #####
def count_xml_files(directory):
    # Count the number of XML files in the directory
    return sum(1 for filename in os.listdir(directory) if filename.endswith('.xml'))

def sanitize_filename(name):
    # Replace any invalid characters in the filename with underscores
    return re.sub(r'[\\/:*?"<>|]', '_', name).rstrip()

def select_directory(variable, label):
    # Show a dialog to select a directory
    directory = filedialog.askdirectory()
    if directory:
        # Set the variable to the selected directory
        variable.set(directory)
        
        # Update the label to show the selected directory
        label.config(text=directory)
        
        # If the variable is the input directory
        if variable == input_dir:  
            # Clear the PNG and XML listboxes
            listbox_png.delete(0, tk.END)
            listbox_xml.delete(0, tk.END)

            # For each file in the directory
            for filename in os.listdir(directory):
                # If the file is an XML file
                if filename.endswith('.xml'):
                    # Add the corresponding PNG file to the PNG list
                    listbox_png.insert(tk.END, os.path.splitext(filename)[0] + '.png')

            def on_select_png(evt):
                # Clear the XML list
                listbox_xml.delete(0, tk.END)

                # Get the selected PNG filename
                png_filename = listbox_png.get(listbox_png.curselection())
                
                # Replace the extension with .xml to get the XML filename
                xml_filename = os.path.splitext(png_filename)[0] + '.xml'

                # Parse the XML file
                tree = ET.parse(os.path.join(directory, xml_filename))
                root = tree.getroot()
                names = set()
                
                # For each SubTexture in the XML file
                for subtexture in root.findall(".//SubTexture"):
                    # Get the name of the SubTexture
                    name = subtexture.get('name')
                    
                    # Remove any trailing digits from the name
                    name = re.sub(r'\d{1,4}(?:\.png)?$', '', name).rstrip()
                    
                    # Add the name to name list
                    names.add(name)

                # For each name in the set of names
                for name in names:
                    # Add the name to the XML list
                    listbox_xml.insert(tk.END, name)

            # Bind the select event of the PNG list to the on_select_png function
            listbox_png.bind('<<ListboxSelect>>', on_select_png)
            
            # Bind the double click event of the XML list to the on_double_click_xml function
            listbox_xml.bind('<Double-1>', on_double_click_xml)
    return directory

# Create an empty dictionary to store the user's input
user_settings = {}

# Creates a window where the user can see what settings they have set for individual animations
def create_settings_window():
    global settings_window
    settings_window = tk.Toplevel()
    settings_window.geometry("400x300")
    # Updates the settings window whenever the Show User Settings button is pressed.
    update_settings_window()

# Updates the settings window with the current user settings.
def update_settings_window():
    if settings_window.winfo_exists():
        for widget in settings_window.winfo_children():
            widget.destroy()

        tk.Label(settings_window, text="User Settings").pack()
        for key, value in user_settings.items():
            tk.Label(settings_window, text=f"{key}: {value}").pack()

# This function is called when the user double-clicks on an animation in the XML list
def on_double_click_xml(evt):
    # Get the name of the selected spritesheet from the PNG list
    spritesheet_name = listbox_png.get(listbox_png.curselection())
    
    # Get the name of the selected animation from the XML list
    animation_name = listbox_xml.get(listbox_xml.curselection())
   
     # Create a new top-level window
    new_window = tk.Toplevel()

    # Set the size of the new window
    new_window.geometry("360x240")

    # Add a label to the new window with the text "FPS for [animation name]"
    tk.Label(new_window, text="FPS for " + animation_name).pack()
    
    # Add an entry field to the new window for the user to input the FPS for the selected animation
    fps_entry = tk.Entry(new_window)
    fps_entry.pack()

    # Add a label to the new window with the text "Delay for [animation name]"
    tk.Label(new_window, text="Delay for " + animation_name).pack()
    
    # Add an entry field to the new window for the user to input the delay for the selected animation
    delay_entry = tk.Entry(new_window)
    delay_entry.pack()
    
    # Add an entry field to the new window for the user to input the threshold for handling semi-transparent pixels for the selected animation
    tk.Label(new_window, text="Threshold for " + animation_name).pack()
    threshold_entry = tk.Entry(new_window)
    threshold_entry.pack()

    # Add an entry field to the new window for the user to input the frame indices for the selected animation
    tk.Label(new_window, text="Indices for " + animation_name).pack()
    indices_entry = tk.Entry(new_window)
    indices_entry.pack()

    # This function is called when the user clicks the OK button
    def store_input():
        
        # Create an empty dictionary to store the user's input for the particular animation
        anim_settings = {}
        
        try:
            # Add the fps entry if not empty
            if fps_entry.get() != '':
                anim_settings['fps'] = float(fps_entry.get())

        # If the fps entry is not a valid float, show an error message and exit the function
        except ValueError:
            messagebox.showerror("Invalid input", "Please enter a valid float for FPS.")
            
            # Raise the new window to the top of the window stack
            new_window.lift()
            return
        try:
            # Add the delay entry if not empty
            if delay_entry.get() != '':
                anim_settings['delay'] = int(delay_entry.get())
                
        # If the delay entry is not a valid integer, show an error message and exit the function
        except ValueError:
            messagebox.showerror("Invalid input", "Please enter a valid integer for delay.")
            
            # Raise the new window to the top of the window stack
            new_window.lift()
            return
        try:
            # Add the threshold entry if not empty
            if threshold_entry.get() != '':
                anim_settings['threshold'] = float(threshold_entry.get())
                
        # If the threshold entry is not a valid float, show an error message and exit the function
        except ValueError:
            messagebox.showerror("Invalid input", "Please enter a valid float for threshold.")
            
            # Raise the new window to the top of the window stack
            new_window.lift()
            return
        try:
            # Add the indices entry if not empty
            if indices_entry.get() != '':

                # Convert the CSV string to an integer list
                indices = [int(ele) for ele in indices_entry.get().split(',')]
                anim_settings['indices'] = indices
                
        # If the indices entry cannot be converted, show an error message and exit the function
        except ValueError:
            messagebox.showerror("Invalid input", "Please enter a comma-separated list of integers for indices.")
            
            # Raise the new window to the top of the window stack
            new_window.lift()
            return
            
        # If there is at least one non-empty setting
        if len(anim_settings) > 0:
            
            # Store the user's input in the "user_settings" dictionary
            user_settings[spritesheet_name + '/' + animation_name] = anim_settings
            
        # If there are no settings but there are previous settings for the given animation
        elif user_settings.get(spritesheet_name + '/' + animation_name):
            
            # Remove the settings for the animation
            user_settings.pop(spritesheet_name + '/' + animation_name)
        
        # Close the new window
        new_window.destroy()

    # Add an OK button to the new window that calls the store_input function when clicked
    tk.Button(new_window, text="OK", command=store_input).pack()

# This function processes a directory of .png and .xml files, creating sprites and optionally .gif and .webp files
def process_directory(input_dir, output_dir, progress_var, tk_root, create_gif, create_webp, keep_frames, set_framerate, set_loopdelay, set_threshold):
    # If none of the gif, webp or frames options are set, stop
    if not (create_gif or create_webp or keep_frames):
        return
    
    # Reset the progress bar
    progress_var.set(0)
    
    # Count the total number of .xml files in the input directory
    total_files = count_xml_files(input_dir)
    
    # Set the maximum value of the progress bar to the total number of files
    progress_bar["maximum"] = total_files

    # Determine the maximum number of worker threads to use
    max_workers = os.cpu_count() // 2
    
    # Create a ThreadPoolExecutor
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        # Iterate over all files in the input directory
        for filename in os.listdir(input_dir):
            # If the file is a .png file
            if filename.endswith('.png'):
                # Create the corresponding .xml filename
                xml_filename = filename.rsplit('.', 1)[0] + '.xml'

                # Create the full path to the .xml file
                xml_path = os.path.join(input_dir, xml_filename)

                # If the .xml file exists
                if os.path.isfile(xml_path):
                    # Create the output directory for the sprites
                    sprite_output_dir = os.path.join(output_dir, filename.rsplit('.', 1)[0])
                    
                    # Ensure the output directory exists
                    os.makedirs(sprite_output_dir, exist_ok=True)
                    
                    # Submit a task to the executor to extract the sprites from the .png file
                    future = executor.submit(extract_sprites, os.path.join(input_dir, filename), xml_path, sprite_output_dir, create_gif, create_webp, keep_frames, set_framerate, set_loopdelay, set_threshold)
                    
                    # Add the Future object to the list of futures
                    futures.append(future)

        # Iterate over the futures as they complete
        for future in concurrent.futures.as_completed(futures):
            try:
                # Get the result of the future, re-raising any exceptions that occurred
                future.result()

            except ET.ParseError as e:
                # Show an error message if there was a problem parsing the .xml file
                messagebox.showerror("Error", f"Something went wrong!!\n{e}")
                
                # Ask the user if they want to continue processing the remaining files
                if not messagebox.askyesno("Continue?", "Do you want to try continue processing?"):
                    sys.exit()

            except Exception as e:
                # Show an error message for any other exceptions
                messagebox.showerror("Error", f"Something went wrong!!\n{str(e)}")
                
                # Ask the user if they want to continue processing the remaining files
                if not messagebox.askyesno("Continue?", "Do you want to try continue processing?"):
                    sys.exit()

            # Increment the progress bar
            progress_var.set(progress_var.get() + 1)

            # Update any pending idle tasks in the Tkinter event loop
            tk_root.update_idletasks()

    # Show an information message when all files have been processed
    messagebox.showinfo("Information","Finished processing all files.")

##### Extraction logic #####
# This function extracts sprites from an atlas and saves them as .png, .gif, and .webp files
def extract_sprites(atlas_path, xml_path, output_dir, create_gif, create_webp, keep_frames, set_framerate, set_loopdelay, set_threshold):
    try:
        # Open the atlas image
        atlas = Image.open(atlas_path)
        
        # Parse the XML file
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        # Initialize a dictionary to store animations
        animations = {}
        
        spritesheet_name = os.path.split(atlas_path)[1]

        # Iterate over all SubTexture elements in the XML file
        for sprite in root.findall('SubTexture'):
            # Get the name and dimensions of the sprite
            name = sprite.get('name')
            x, y, width, height = map(int, (sprite.get(attr) for attr in ('x', 'y', 'width', 'height')))
            
            # Get the frame dimensions and rotation status of the sprite, ensuring the width and height are at least 1
            frameX = int(sprite.get('frameX', 0))
            frameY = int(sprite.get('frameY', 0))
            frameWidth = max(int(sprite.get('frameWidth', width)), 1)
            frameHeight = max(int(sprite.get('frameHeight', height)), 1)
            rotated = sprite.get('rotated', 'false') == 'true'

            # Crop the sprite image from the atlas using the prcoessed xml files
            sprite_image = atlas.crop((x, y, x + width, y + height))
           
            # If the atlas has rotated frames, rotate the frame counter-clockwise
            if rotated: 
                sprite_image = sprite_image.rotate(90, expand=True)

            # Create a new image for the frame and paste the sprite image onto it
            frame_image = Image.new('RGBA', (frameWidth, frameHeight))
            frame_image.paste(sprite_image, (-frameX, -frameY))

            # Convert color mode to RGBA if it isn't already
            if frame_image.mode != 'RGBA':
                frame_image = frame_image.convert('RGBA')

            # Create a new directory using the animation name to store the frames neatly
            folder_name = re.sub(r'\d{1,4}(?:\.png)?$', '', name).rstrip()
            sprite_folder = os.path.join(output_dir, folder_name)
            os.makedirs(sprite_folder, exist_ok=True)

            # Save the frame image as a .png file
            frame_image.save(os.path.join(sprite_folder, f"{name}.png"))

            # If .gif or .webp files should be created, add the frame image to the animations dictionary
            if create_gif or create_webp:
                animations.setdefault(folder_name, []).append(frame_image)
                
        for animation_name, images in animations.items():
            # Get the settings for the current animation from the "user_settings" dictionary
            # If the "spritesheet_name" and "animation_name" does not exist in the dictionary, use the global settings
            settings = user_settings.get(spritesheet_name + '/' + animation_name, {})
            fps = settings.get('fps', set_framerate)
            delay = settings.get('delay', set_loopdelay)
            threshold = settings.get('threshold', set_threshold)
            indices = settings.get('indices')

            # If there are indices set, replace the image list to store the images of the chosen indices
            if indices:
                indices = list(filter(lambda i: ((i < len(images)) & (i >= 0)), indices))
                images = [images[i] for i in indices]

            # Get the minimum and maximum sizes of the frames
            sizes = [frame.size for frame in images]
            max_size = tuple(map(max, zip(*sizes)))
            min_size = tuple(map(min, zip(*sizes)))

            # If they are different, expand the frames to the maximum size 
            if max_size != min_size:
                for index, frame in enumerate(images):
                    images[index] = Image.new('RGBA', max_size)
                    images[index].paste(frame)
            
            # If .webp files should be created   
            if create_webp:

                # Set the durations for each frame
                durations = [round(1000/fps)] * len(images)

                # Add the delay to the final frame
                durations[-1] += delay

                # Save as .webp
                images[0].save(os.path.join(output_dir, os.path.splitext(spritesheet_name)[0] + f" {animation_name}.webp"), save_all=True, append_images=images[1:], disposal=2, duration=durations, loop=0, lossless=True)

            # If .gif files should be created
            if create_gif:
                
                # Change semi-transparent pixels to be fully opaque or fully transparent based on the threshold
                for frame in images:
                    alpha = frame.getchannel('A')
                    alpha = alpha.point(lambda i: i > 255*threshold and 255)
                    frame.putalpha(alpha)
                durations = [round(1000/fps)] * len(images)
                durations[-1] += delay
                images[0].save(os.path.join(output_dir, os.path.splitext(spritesheet_name)[0] + f" {animation_name}.gif"), save_all=True, append_images=images[1:], disposal=2, optimize=False, duration=durations, loop=0)

            # If frames should not be kept
            if not keep_frames:

                # Get the folder that stores the frames for the animation
                frames_folder = os.path.join(output_dir, animation_name)

                # Delete all the files in the folder
                for i in os.listdir(frames_folder):
                    os.remove(os.path.join(frames_folder, i))

                # Delete the folder
                os.rmdir(frames_folder)
    
    # If there's a problem parsing the XML file, raise a ParseError
    except ET.ParseError:
        raise ET.ParseError(f"Badly formatted XML file:\n{xml_path}")
    # If any other exception occurs, re-raise it
    except Exception as e:
        raise Exception(f"An error occurred: {str(e)}")


##### Graphical User Interface setup #####
# Create a root window with tkinter
root = tk.Tk()
# Set the title of the window
root.title("TextureAtlas to GIF and Frames")
# Set the size of the window
root.geometry("900x480")
# Make the window non-resizable
root.resizable(False, False)

# Create a variable to track progress
progress_var = tk.DoubleVar()
# Create a progress bar and add it to the root window
progress_bar = ttk.Progressbar(root, length=865, variable=progress_var)
progress_bar.pack(pady=8)

# Create a scrollbar for the PNG listbox
scrollbar_png = tk.Scrollbar(root)
scrollbar_png.pack(side=tk.LEFT, fill=tk.Y)

# Create a listbox for PNG files and link it to the scrollbar
listbox_png = tk.Listbox(root, width=30, exportselection=0, yscrollcommand=scrollbar_png.set)
listbox_png.pack(side=tk.LEFT, fill=tk.Y)

# Create a scrollbar for the XML listbox
scrollbar_xml = tk.Scrollbar(root)
scrollbar_xml.pack(side=tk.LEFT, fill=tk.Y)

# Create a listbox for XML files and link it to the scrollbar
listbox_xml = tk.Listbox(root, width=30, yscrollcommand=scrollbar_xml.set)
listbox_xml.pack(side=tk.LEFT, fill=tk.Y)

# Link the scrollbars to the listboxes
scrollbar_png.config(command=listbox_png.yview)
scrollbar_xml.config(command=listbox_xml.yview)

# Create a variable to hold the input directory
input_dir = tk.StringVar()
# Create a button to select the input directory and clear the user settings
input_button = tk.Button(root, text="Select directory with spritesheets", cursor="hand2", command=lambda: select_directory(input_dir, input_dir_label) and user_settings.clear())
input_button.pack(pady=2)

# Create a label to display the selected input directory
input_dir_label = tk.Label(root, text="No input directory selected")
input_dir_label.pack(pady=4)

# Create a variable to hold the output directory
output_dir = tk.StringVar()
# Create a button to select the output directory
output_button = tk.Button(root, text="Select save directory", cursor="hand2", command=lambda: select_directory(output_dir, output_dir_label))
output_button.pack(pady=2)

# Create a label to display the selected output directory
output_dir_label = tk.Label(root, text="No output directory selected")
output_dir_label.pack(pady=4)

# Create a variable to hold the gif creation option
create_gif = tk.BooleanVar()
# Create a checkbox to select the gif creation option
gif_checkbox = tk.Checkbutton(root, text="Create GIFs for each animation", variable=create_gif)
gif_checkbox.pack()

# Create a variable to hold the webp creation option
create_webp = tk.BooleanVar()
# Create a checkbox to select the webp creation option
webp_checkbox = tk.Checkbutton(root, text="Create WebPs for each animation", variable=create_webp)
webp_checkbox.pack()

# Create a variable to hold the frame creation option
keep_frames = tk.BooleanVar()
# Create a checkbox to select the frame creation option
frame_checkbox = tk.Checkbutton(root, text="Keep individual frames", variable=keep_frames)
frame_checkbox.pack()

# Create a variable to hold the frame rate
set_framerate = tk.DoubleVar(value=24)
# Create a label and entry field for the frame rate
frame_rate_label = tk.Label(root, text="Frame Rate (fps):")
frame_rate_label.pack()
frame_rate_entry = tk.Entry(root, textvariable=set_framerate)
frame_rate_entry.pack()

# Create a variable to hold the loop delay
set_loopdelay = tk.DoubleVar(value=0)
# Create a label and entry field for the loop delay
loopdelay_label = tk.Label(root, text="Loop Delay (ms):")
loopdelay_label.pack()
loopdelay_entry = tk.Entry(root, textvariable=set_loopdelay)
loopdelay_entry.pack()

# Create a variable to hold the alpha threshold. This value is used to determine which pixels are considered transparent when creating the GIFs
set_threshold = tk.DoubleVar(value=0.5)
# Create a label and entry field for the alpha threshold
threshold_label = tk.Label(root, text="Alpha Threshold:")
threshold_label.pack()
threshold_entry = tk.Entry(root, textvariable=set_threshold)
threshold_entry.pack()

process_button = tk.Button(root, text="Start process", cursor="hand2", command=lambda: process_directory(input_dir.get(), output_dir.get(), progress_var, root, create_gif.get(), create_webp.get(), keep_frames.get(), set_framerate.get(), set_loopdelay.get(), set_threshold.get()))
process_button.pack(pady=8)

# Button frame to hold the buttons.
button_frame = tk.Frame(root)
button_frame.pack(pady=8)

# Create a button to show user settings
show_user_settings = tk.Button(button_frame, text="Show User Settings", command=create_settings_window)
show_user_settings.pack(side=tk.LEFT, padx=4)

# Create a button to start the processing
process_button = tk.Button(button_frame, text="Start process", cursor="hand2", command=lambda: process_directory(input_dir.get(), output_dir.get(), progress_var, root, create_gif.get(), create_webp.get(), keep_frames.get(), set_framerate.get(), set_loopdelay.get(), set_threshold.get()))
process_button.pack(side=tk.LEFT, padx=4)

# Create a label to display the author's name
author_label = tk.Label(root, text="Project started by AutisticLulu")
author_label.pack(side='bottom')

# Function to open a URL in a new browser window
def contributeLink(url):
    webbrowser.open_new(url)

# Create a link to the source code
linkSourceCode = "https://github.com/MeguminBOT/TextureAtlas-to-GIF-and-Frames"
link1 = tk.Label(root, text="If you wish to contribute to the project, click here!", fg="blue", cursor="hand2")
link1.pack(side='bottom')
# Bind the link to the function to open the URL
link1.bind("<Button-1>", lambda e: contributeLink(linkSourceCode))

##### Main loop #####
root.mainloop()
