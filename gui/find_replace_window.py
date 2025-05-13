import tkinter as tk
from tkinter import ttk

class FindReplaceWindow:
    """
    A window for managing find-and-replace rules for filenames.

    This class creates a Tkinter window that allows the user to add, edit, and delete find-and-replace rules,
    including support for regular expressions, to be applied to exported filenames.

    Attributes:
        replace_window (tk.Toplevel): The Tkinter window instance.
        replace_rules (list): The list of current find-and-replace rules.
        on_store_callback (callable): Callback function to call when the user confirms the changes.
        rules_frame (tk.Frame): Frame containing the rule entry widgets.

    Methods:
        add_replace_rule(rule):
            Adds a new rule entry row to the window.
        store_replace_rules():
            Collects all rule entries and calls the callback with the updated rules.
    """
    def __init__(self, parent, replace_rules, on_store_callback):
        self.replace_window = tk.Toplevel(parent)
        self.replace_window.geometry("400x300")
        tk.Label(self.replace_window, text="Find and replace").pack()
        self.rules_frame = tk.Frame(self.replace_window)
        self.rules_frame.pack()
        self.replace_rules = replace_rules
        self.on_store_callback = on_store_callback

        add_button = tk.Button(self.replace_window, text='Add rule', command=lambda: self.add_replace_rule({"find":"","replace":"","regex":False}))
        add_button.pack()
        for rule in self.replace_rules:
            self.add_replace_rule(rule)
        ok_button = tk.Button(self.replace_window, text='OK', command=self.store_replace_rules)
        ok_button.pack()

    def add_replace_rule(self, rule):
        frame = tk.Frame(self.rules_frame, borderwidth=2, relief='sunken')
        find_entry = tk.Entry(frame, width=40)
        find_entry.insert(0, rule["find"])
        find_entry.pack()
        replace_entry = tk.Entry(frame, width=40)
        replace_entry.insert(0, rule["replace"])
        replace_entry.pack()
        regex_checkbox = ttk.Checkbutton(frame, text="Regular expression")
        regex_checkbox.pack()
        delete_rule_button = tk.Button(frame, text="Delete", command=lambda: frame.destroy())
        delete_rule_button.pack()
        regex_checkbox.invoke()
        if not rule["regex"]:
            regex_checkbox.invoke()
        frame.pack(pady=2)
        self.rules_frame.update()
        return frame

    def store_replace_rules(self):
        rules = []
        for rule in self.rules_frame.winfo_children():
            rule_settings = rule.winfo_children()
            rules.append({
                "find": rule_settings[0].get(),
                "replace": rule_settings[1].get(),
                "regex": "selected" in rule_settings[2].state()
            })
        self.on_store_callback(rules)
        self.replace_window.destroy()