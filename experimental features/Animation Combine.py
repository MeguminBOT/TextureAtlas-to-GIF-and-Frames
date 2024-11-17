# File: gif_combiner.py

import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk, ImageSequence
import os


class GifCombinerApp:
	def __init__(self, root):
		self.root = root
		self.root.title("GIF Combiner")

		self.gifs = []  # List of {"frames": [], "canvas_obj": ..., "x": ..., "y": ..., "scale": ..., "duration": ...}
		self.current_frame = 0
		self.history = []  # History undo/redo
		self.redo_stack = []

		self.canvas_width = 800
		self.canvas_height = 600

		self.setup_ui()

	def setup_ui(self):
		tk.Button(self.root, text="Load GIF", command=self.load_gif).pack(side=tk.TOP, fill=tk.X)
		tk.Button(self.root, text="Export Combined GIF", command=self.export_gif).pack(side=tk.TOP, fill=tk.X)
		tk.Button(self.root, text="Preview Combined Animation", command=self.preview_combined).pack(side=tk.TOP, fill=tk.X)
		tk.Button(self.root, text="Undo", command=self.undo).pack(side=tk.LEFT, padx=5)
		tk.Button(self.root, text="Redo", command=self.redo).pack(side=tk.LEFT, padx=5)

		self.timeline_frame = tk.Frame(self.root)
		self.timeline_frame.pack(side=tk.BOTTOM, fill=tk.X)
		tk.Label(self.timeline_frame, text="Frame Duration (ms):").pack(side=tk.LEFT)
		self.timeline_slider = tk.Scale(self.timeline_frame, from_=10, to=500, resolution=10, orient=tk.HORIZONTAL)
		self.timeline_slider.set(100)
		self.timeline_slider.pack(side=tk.LEFT)
		tk.Button(self.timeline_frame, text="Apply Duration", command=self.apply_duration).pack(side=tk.LEFT)

		self.canvas = tk.Canvas(self.root, width=self.canvas_width, height=self.canvas_height, bg="white")
		self.canvas.pack(expand=True, fill=tk.BOTH)
		self.canvas.bind("<Configure>", self.on_canvas_resize)

		self.position_frame = tk.Frame(self.root)
		self.position_frame.pack(side=tk.BOTTOM, fill=tk.X)
		tk.Label(self.position_frame, text="X:").pack(side=tk.LEFT)
		self.x_entry = tk.Entry(self.position_frame, width=5)
		self.x_entry.pack(side=tk.LEFT)
		tk.Label(self.position_frame, text="Y:").pack(side=tk.LEFT)
		self.y_entry = tk.Entry(self.position_frame, width=5)
		self.y_entry.pack(side=tk.LEFT)
		tk.Button(self.position_frame, text="Set Position", command=self.set_position).pack(side=tk.LEFT)

		self.scale_frame = tk.Frame(self.root)
		self.scale_frame.pack(side=tk.BOTTOM, fill=tk.X)
		tk.Label(self.scale_frame, text="Scale:").pack(side=tk.LEFT)
		self.scale_slider = tk.Scale(self.scale_frame, from_=0.1, to=3.0, resolution=0.1, orient=tk.HORIZONTAL)
		self.scale_slider.set(1.0)
		self.scale_slider.pack(side=tk.LEFT)
		tk.Button(self.scale_frame, text="Apply Scale", command=self.apply_scale).pack(side=tk.LEFT)
		self.update_canvas()

	def preview_combined(self):
		preview_window = tk.Toplevel(self.root)
		preview_window.title("Combined Animation Preview")
		preview_canvas = tk.Canvas(preview_window, width=800, height=600, bg="white")
		preview_canvas.pack(expand=True, fill=tk.BOTH)

		def animate_preview(self, frame_idx=0):
			preview_canvas.delete("all")
			preview_width = preview_canvas.winfo_width()
			preview_height = preview_canvas.winfo_height()

			# Scale all GIFs to fit within the preview canvas
			for gif_data in self.gifs:
				frames = gif_data["frames"]
				x, y, scale = gif_data["x"], gif_data["y"], gif_data["scale"]

				# Fit the GIF within the window dimensions
				max_width = int(preview_width * 0.8)  # 80% of the preview window's width
				max_height = int(preview_height * 0.8)  # 80% of the preview window's height

				# Resize image to fit within the window while maintaining aspect ratio
				resized_frame = frames[frame_idx % len(frames)]
				frame_width, frame_height = resized_frame.width(), resized_frame.height()

				aspect_ratio = frame_width / frame_height
				new_width = min(max_width, int(max_height * aspect_ratio))
				new_height = min(max_height, int(max_width / aspect_ratio))

				# Resize the frame based on scale and preview window size
				resized_frame = resized_frame.subsample(
					int(frame_width / new_width), int(frame_height / new_height)
				)

				# Scale the frame according to its current zoom level
				preview_canvas.create_image(x, y, image=resized_frame, anchor=tk.CENTER)

			frame_idx += 1
			preview_window.after(100, animate_preview, frame_idx)  # Delay to animate frames


		preview_canvas.bind("<Configure>", lambda e: animate_preview())
		preview_canvas.bind("<MouseWheel>", self.zoom_preview)

		animate_preview()

	def zoom_preview(self, event):
		# Zoom in or out based on mouse wheel direction
		zoom_factor = 1.1
		if event.delta < 0:  # Zoom out
			zoom_factor = 0.9

		# Apply zoom to all GIFs in preview
		for gif_data in self.gifs:
			gif_data["scale"] *= zoom_factor  # Adjust scale factor for each gif

		self.preview_combined()  # Refresh preview with new scale


	def load_gif(self):
		filepath = filedialog.askopenfilename(filetypes=[("GIF Files", "*.gif")])
		if not filepath:
			return

		# Load the original GIF
		gif = Image.open(filepath)

		# Store PIL.Image frames and also create initial PhotoImage objects for rendering
		pil_frames = [frame.copy() for frame in ImageSequence.Iterator(gif)]
		photo_frames = [ImageTk.PhotoImage(frame) for frame in pil_frames]

		x, y, scale, duration = 100, 100, 1.0, 100
		canvas_obj = self.canvas.create_image(x, y, image=photo_frames[0], anchor=tk.CENTER)

		gif_data = {
			"pil_frames": pil_frames,  # Store original frames as PIL.Image
			"frames": photo_frames,  # Store PhotoImage for rendering
			"canvas_obj": canvas_obj,
			"x": x,
			"y": y,
			"scale": scale,
			"duration": duration,
			"filepath": filepath,  # Save filepath for debugging or reloading if necessary
		}
		self.gifs.append(gif_data)
		self.save_history("load", gif_data)

	def on_canvas_resize(self, event):
		new_width, new_height = event.width, event.height
		scale_x = new_width / self.canvas_width
		scale_y = new_height / self.canvas_height

		for gif_data in self.gifs:
			gif_data["x"] = int(gif_data["x"] * scale_x)
			gif_data["y"] = int(gif_data["y"] * scale_y)
			gif_data["frames"] = [
				ImageTk.PhotoImage(
					frame.resize(
						(
							int(frame.width * gif_data["scale"] * scale_x),
							int(frame.height * gif_data["scale"] * scale_y),
						),
						Image.ANTIALIAS,
					)
				)
				for frame in gif_data["pil_frames"]  # Use PIL.Image for resizing
			]
			self.canvas.coords(gif_data["canvas_obj"], gif_data["x"], gif_data["y"])

		self.canvas_width, self.canvas_height = new_width, new_height


	def set_position(self):
		if not self.gifs:
			return

		try:
			x = int(self.x_entry.get())
			y = int(self.y_entry.get())
			gif_data = self.gifs[-1]
			self.save_history("position", gif_data.copy())
			gif_data["x"] = x
			gif_data["y"] = y
			self.canvas.coords(gif_data["canvas_obj"], x, y)
		except ValueError:
			print("Invalid position values")

	def apply_scale(self):
		if not self.gifs:
			return

		try:
			scale = float(self.scale_slider.get())
			gif_data = self.gifs[-1]
			self.save_history("scale", gif_data.copy())
			gif_data["scale"] = scale
		except Exception as e:
			print(f"Error applying scale: {e}")

	def apply_duration(self):
		if not self.gifs:
			return

		duration = int(self.timeline_slider.get())
		gif_data = self.gifs[-1]
		self.save_history("duration", gif_data.copy())
		gif_data["duration"] = duration

	def save_history(self, action, gif_data):
		self.history.append({"action": action, "gif_data": gif_data})
		self.redo_stack.clear()

	def undo(self):
		if not self.history:
			return

		last_action = self.history.pop()
		self.redo_stack.append(last_action)

		if last_action["action"] == "position":
			last_action["gif_data"]["x"] = last_action["gif_data"]["x"]
			last_action["gif_data"]["y"] = last_action["gif_data"]["y"]
			self.canvas.coords(
				last_action["gif_data"]["canvas_obj"],
				last_action["gif_data"]["x"],
				last_action["gif_data"]["y"],
			)
		elif last_action["action"] == "scale":
			self.apply_scale()
		elif last_action["action"] == "duration":
			self.apply_duration()

	def redo(self):
		if not self.redo_stack:
			return

		redo_action = self.redo_stack.pop()
		self.history.append(redo_action)

		if redo_action["action"] == "position":
			self.set_position()
		elif redo_action["action"] == "scale":
			self.apply_scale()
		elif redo_action["action"] == "duration":
			self.apply_duration()

	def update_canvas(self):
		if self.gifs:
			for gif_data in self.gifs:
				frames = gif_data["frames"]
				canvas_obj = gif_data["canvas_obj"]
				self.canvas.itemconfig(canvas_obj, image=frames[self.current_frame % len(frames)])

		self.current_frame += 1
		self.root.after(100, self.update_canvas)

	def preview_combined(self):
		preview_window = tk.Toplevel(self.root)
		preview_window.title("Combined Animation Preview")
		preview_canvas = tk.Canvas(preview_window, width=800, height=600, bg="white")
		preview_canvas.pack(expand=True, fill=tk.BOTH)

		def animate_preview(frame_idx=0):
			preview_canvas.delete("all")
			for gif_data in self.gifs:
				frames = gif_data["frames"]
				x, y, scale = gif_data["x"], gif_data["y"], gif_data["scale"]
				preview_canvas.create_image(x, y, image=frames[frame_idx % len(frames)], anchor=tk.CENTER)
			frame_idx += 1
			preview_window.after(100, animate_preview, frame_idx)

		animate_preview()

	def export_gif(self):
		output_frames = []
		max_frames = max(len(gif_data["pil_frames"]) for gif_data in self.gifs)

		for frame_idx in range(max_frames):
			frame_image = Image.new("RGBA", (self.canvas_width, self.canvas_height), (255, 255, 255, 0))
			for gif_data in self.gifs:
				pil_frames = gif_data["pil_frames"]
				x, y, scale = gif_data["x"], gif_data["y"], gif_data["scale"]

				gif_frame = pil_frames[frame_idx % len(pil_frames)].copy()
				gif_frame = gif_frame.resize(
					(int(gif_frame.width * scale), int(gif_frame.height * scale)), Image.ANTIALIAS
				)
				frame_image.paste(
					gif_frame,
					(x - gif_frame.width // 2, y - gif_frame.height // 2),
					gif_frame,
				)

			output_frames.append(frame_image)

		output_path = filedialog.asksaveasfilename(defaultextension=".gif", filetypes=[("GIF Files", "*.gif")])
		if output_path:
			output_frames[0].save(
				output_path,
				save_all=True,
				append_images=output_frames[1:],
				duration=self.timeline_slider.get(),
				loop=0,
			)
			print(f"GIF saved to {output_path}")


if __name__ == "__main__":
	root = tk.Tk()
	app = GifCombinerApp(root)
	root.mainloop()
