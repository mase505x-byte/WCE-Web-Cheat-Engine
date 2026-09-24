import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import time
import json
import re
from selenium import webdriver  # type: ignore[import-not-found]
from selenium.webdriver.common.by import By  # type: ignore[import-not-found]
from selenium.common.exceptions import StaleElementReferenceException  # type: ignore[import-not-found]


class WebCheatEngine:
    """
    A mini cheat engine for websites that allows scanning and modifying values
    in web pages using Selenium browser automation.
    """

    def __init__(self, root):
        self.root = root
        self.root.title("Web Cheat Engine - Mini Edition")
        self.root.geometry("900x700")

        # Browser driver
        self.driver = None
        self.current_url = ""

        # Scan results storage
        self.scan_results = []
        self.original_values = {}
        self.selected_result = None

        # Setup GUI
        self.setup_gui()

        # Status variables
        self.is_scanning = False
        self.scan_thread = None

    def setup_gui(self):
        """Setup the main GUI layout"""

        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=5, pady=5)

        # Create tabs
        self.scan_tab = ttk.Frame(self.notebook)
        self.value_tab = ttk.Frame(self.notebook)
        self.monitor_tab = ttk.Frame(self.notebook)
        self.console_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.scan_tab, text='Scanner')
        self.notebook.add(self.value_tab, text='Value Editor')
        self.notebook.add(self.monitor_tab, text='Monitor')
        self.notebook.add(self.console_tab, text='Console')

        # Setup each tab
        self.setup_browser_controls()
        self.setup_scan_tab()
        self.setup_value_tab()
        self.setup_monitor_tab()
        self.setup_console_tab()

        # Status bar
        self.status_bar = ttk.Label(self.root, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def setup_browser_controls(self):
        """Setup browser control buttons"""
        browser_frame = ttk.LabelFrame(self.root, text="Browser Controls", padding=5)
        browser_frame.pack(fill=tk.X, padx=5, pady=5)

        # URL entry
        ttk.Label(browser_frame, text="URL:").pack(side=tk.LEFT, padx=5)
        self.url_var = tk.StringVar(value="https://example.com")
        self.url_entry = ttk.Entry(browser_frame, textvariable=self.url_var, width=50)
        self.url_entry.pack(side=tk.LEFT, padx=5)

        # Buttons
        ttk.Button(browser_frame, text="Connect", command=self.connect_browser).pack(side=tk.LEFT, padx=5)
        ttk.Button(browser_frame, text="Refresh", command=self.refresh_browser).pack(side=tk.LEFT, padx=5)
        ttk.Button(browser_frame, text="Disconnect", command=self.disconnect_browser).pack(side=tk.LEFT, padx=5)

    def setup_scan_tab(self):
        """Setup the scanning interface"""
        # Scan controls
        scan_frame = ttk.LabelFrame(self.scan_tab, text="Scan Controls", padding=5)
        scan_frame.pack(fill=tk.X, padx=5, pady=5)

        # Value to scan
        ttk.Label(scan_frame, text="Value to scan:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.scan_value = ttk.Entry(scan_frame, width=20)
        self.scan_value.grid(row=0, column=1, padx=5)

        # Scan type
        ttk.Label(scan_frame, text="Scan type:").grid(row=0, column=2, sticky=tk.W, padx=5)
        self.scan_type = ttk.Combobox(scan_frame, values=["Exact", "Contains", "Regex"], state="readonly")
        self.scan_type.set("Exact")
        self.scan_type.grid(row=0, column=3, padx=5)

        # Element selector
        ttk.Label(scan_frame, text="CSS Selector:").grid(row=1, column=0, sticky=tk.W, padx=5)
        self.selector_entry = ttk.Entry(scan_frame, width=30)
        self.selector_entry.grid(row=1, column=1, columnspan=2, sticky=tk.W, padx=5)
        ttk.Button(scan_frame, text="Scan", command=self.start_scan).grid(row=1, column=3, padx=5)

        # Results tree
        results_frame = ttk.LabelFrame(self.scan_tab, text="Scan Results", padding=5)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Treeview for results
        self.results_tree = ttk.Treeview(results_frame, columns=("Selector", "Value", "Tag"), show="headings", height=10)
        self.results_tree.heading("Selector", text="CSS Selector")
        self.results_tree.heading("Value", text="Current Value")
        self.results_tree.heading("Tag", text="HTML Tag")

        self.results_tree.column("Selector", width=300)
        self.results_tree.column("Value", width=150)
        self.results_tree.column("Tag", width=100)

        # Scrollbar
        scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.results_tree.yview)
        self.results_tree.configure(yscrollcommand=scrollbar.set)

        self.results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Bind selection
        self.results_tree.bind('<<TreeviewSelect>>', self.on_result_select)

    def setup_value_tab(self):
        """Setup the value editor interface"""
        # Editor frame
        editor_frame = ttk.LabelFrame(self.value_tab, text="Value Editor", padding=5)
        editor_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Selected element info
        ttk.Label(editor_frame, text="Selected Element:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.selected_element = ttk.Entry(editor_frame, width=50)
        self.selected_element.grid(row=0, column=1, columnspan=3, sticky=tk.W, padx=5)

        # Current value
        ttk.Label(editor_frame, text="Current Value:").grid(row=1, column=0, sticky=tk.W, padx=5)
        self.current_value = ttk.Entry(editor_frame, width=30)
        self.current_value.grid(row=1, column=1, sticky=tk.W, padx=5)

        # New value
        ttk.Label(editor_frame, text="New Value:").grid(row=2, column=0, sticky=tk.W, padx=5)
        self.new_value = ttk.Entry(editor_frame, width=30)
        self.new_value.grid(row=2, column=1, sticky=tk.W, padx=5)

        # Modification type
        ttk.Label(editor_frame, text="Modify:").grid(row=2, column=2, sticky=tk.W, padx=5)
        self.modify_type = ttk.Combobox(editor_frame, values=["Text", "HTML", "Attribute", "Value"], state="readonly")
        self.modify_type.set("Text")
        self.modify_type.grid(row=2, column=3, padx=5)

        # Attribute name (if modifying attribute)
        ttk.Label(editor_frame, text="Attribute:").grid(row=3, column=0, sticky=tk.W, padx=5)
        self.attribute_name = ttk.Entry(editor_frame, width=20)
        self.attribute_name.grid(row=3, column=1, sticky=tk.W, padx=5)

        # Apply button
        ttk.Button(editor_frame, text="Apply Changes", command=self.apply_changes).grid(row=3, column=2, columnspan=2, pady=10)

        # Quick actions
        quick_frame = ttk.LabelFrame(self.value_tab, text="Quick Actions", padding=5)
        quick_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(quick_frame, text="Freeze Value", command=self.freeze_value).pack(side=tk.LEFT, padx=5)
        ttk.Button(quick_frame, text="Reset to Original", command=self.reset_value).pack(side=tk.LEFT, padx=5)
        ttk.Button(quick_frame, text="Save Snapshot", command=self.save_snapshot).pack(side=tk.LEFT, padx=5)

    def setup_monitor_tab(self):
        """Setup the value monitor interface"""
        monitor_frame = ttk.LabelFrame(self.monitor_tab, text="Value Monitor", padding=5)
        monitor_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Monitor controls
        ttk.Label(monitor_frame, text="Polling Interval (ms):").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.poll_interval = ttk.Entry(monitor_frame, width=10)
        self.poll_interval.insert(0, "1000")
        self.poll_interval.grid(row=0, column=1, sticky=tk.W, padx=5)

        self.monitor_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(monitor_frame, text="Enable Monitoring", variable=self.monitor_var,
                       command=self.toggle_monitoring).grid(row=0, column=2, padx=5)

        # Monitor display
        self.monitor_display = scrolledtext.ScrolledText(monitor_frame, height=20, width=80)
        self.monitor_display.grid(row=1, column=0, columnspan=4, padx=5, pady=5)

    def setup_console_tab(self):
        """Setup the console/log output"""
        console_frame = ttk.LabelFrame(self.console_tab, text="Console Output", padding=5)
        console_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.console = scrolledtext.ScrolledText(console_frame, height=20, width=80)
        self.console.pack(fill=tk.BOTH, expand=True)

        # Clear button
        ttk.Button(console_frame, text="Clear Console", command=self.clear_console).pack(pady=5)

    def log_message(self, message, level="INFO"):
        """Log message to console and status bar"""
        timestamp = time.strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}\n"

        self.console.insert(tk.END, log_entry)
        self.console.see(tk.END)

        if level == "ERROR":
            self.status_bar.config(text=f"Error: {message}")
        elif level == "SUCCESS":
            self.status_bar.config(text=message)
        else:
            self.status_bar.config(text=message)

    def clear_console(self):
        """Clear the console output"""
        self.console.delete(1.0, tk.END)

    def connect_browser(self):
        """Connect to browser using Selenium"""
        try:
            self.log_message("Attempting to connect to browser...")

            # Try to connect to existing browser or create new one
            options = webdriver.ChromeOptions()
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')

            # Try to connect to existing session first
            try:
                self.driver = webdriver.Remote(
                    command_executor='http://localhost:9515',
                    options=options
                )
            except Exception:
                # If connection fails, create new browser
                self.driver = webdriver.Chrome(options=options)

            # Navigate to URL
            url = self.url_var.get()
            if not url.startswith('http://') and not url.startswith('https://'):
                url = 'https://' + url

            self.driver.get(url)
            self.current_url = url
            self.log_message(f"Connected to browser. Navigated to: {url}", "SUCCESS")

        except Exception as e:
            self.log_message(f"Failed to connect to browser: {str(e)}", "ERROR")
            messagebox.showerror("Connection Error", f"Failed to connect to browser: {str(e)}")

    def refresh_browser(self):
        """Refresh the current browser page"""
        if self.driver:
            try:
                self.driver.refresh()
                self.log_message("Browser page refreshed", "SUCCESS")
            except Exception as e:
                self.log_message(f"Failed to refresh: {str(e)}", "ERROR")
        else:
            messagebox.showwarning("No Browser", "Please connect to a browser first")

    def disconnect_browser(self):
        """Disconnect from browser"""
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
                self.log_message("Browser disconnected", "SUCCESS")
            except Exception as e:
                self.log_message(f"Error disconnecting: {str(e)}", "ERROR")
        else:
            messagebox.showwarning("No Browser", "Browser is not connected")

    def start_scan(self):
        """Start scanning for values in the web page"""
        if not self.driver:
            messagebox.showwarning("No Browser", "Please connect to a browser first")
            return

        if self.is_scanning:
            return

        self.is_scanning = True
        self.scan_thread = threading.Thread(target=self.scan_webpage)
        self.scan_thread.daemon = True
        self.scan_thread.start()

    def scan_webpage(self):
        """Scan the webpage for matching elements"""
        try:
            self.log_message("Starting scan...")
            self.results_tree.delete(*self.results_tree.get_children())
            self.scan_results = []

            # Get scan parameters
            search_value = self.scan_value.get()
            scan_type = self.scan_type.get()
            selector = self.selector_entry.get() if self.selector_entry.get() else "*"

            # Find all elements
            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)

            for element in elements:
                try:
                    # Get element text and attributes
                    element_text = element.text
                    element_tag = element.tag_name

                    # Check for matches based on scan type
                    match = False
                    if scan_type == "Exact" and element_text == search_value:
                        match = True
                    elif scan_type == "Contains" and search_value in element_text:
                        match = True
                    elif scan_type == "Regex" and search_value:
                        if re.search(search_value, element_text):
                            match = True

                    if match:
                        # Generate a unique selector for this element
                        unique_selector = self.generate_selector(element)

                        # Store result
                        result = {
                            'selector': unique_selector,
                            'value': element_text,
                            'tag': element_tag,
                            'element': element
                        }
                        self.scan_results.append(result)

                        # Add to tree
                        self.results_tree.insert("", tk.END, values=(
                            unique_selector,
                            element_text[:50] + "..." if len(element_text) > 50 else element_text,
                            element_tag
                        ))

                except StaleElementReferenceException:
                    continue

            self.log_message(f"Scan completed. Found {len(self.scan_results)} matching elements", "SUCCESS")

        except Exception as e:
            self.log_message(f"Scan error: {str(e)}", "ERROR")
        finally:
            self.is_scanning = False

    def generate_selector(self, element):
        """Generate a unique CSS selector for an element"""
        try:
            # Try ID
            if element.get_attribute('id'):
                return f"#{element.get_attribute('id')}"

            # Try classes
            classes = element.get_attribute('class')
            if classes:
                class_selector = "." + ".".join(classes.split())
                elements = self.driver.find_elements(By.CSS_SELECTOR, class_selector)
                if len(elements) == 1:
                    return class_selector

            # Generate path from parent
            parts = []
            current = element
            while current.tag_name != "html":
                parent = current.find_element(By.XPATH, "..")
                siblings = parent.find_elements(By.XPATH, f"./{current.tag_name}")

                if len(siblings) == 1:
                    parts.insert(0, current.tag_name)
                else:
                    index = siblings.index(current) + 1
                    parts.insert(0, f"{current.tag_name}:nth-child({index})")

                current = parent

            return " > ".join(parts)

        except Exception:
            return "Unknown selector"

    def on_result_select(self, _event):
        """Handle selection of scan result"""
        selection = self.results_tree.selection()
        if selection:
            item = self.results_tree.item(selection[0])
            values = item['values']

            # Update editor fields
            self.selected_element.delete(0, tk.END)
            self.selected_element.insert(0, values[0])

            self.current_value.delete(0, tk.END)
            self.current_value.insert(0, values[1])

            # Find the element in results
            for result in self.scan_results:
                if result['selector'] == values[0]:
                    self.selected_result = result
                    break

    def apply_changes(self):
        """Apply changes to the selected element"""
        if not hasattr(self, 'selected_result') or self.selected_result is None:
            messagebox.showwarning("No Selection", "Please select an element first")
            return

        try:
            element = self.selected_result['element']
            new_value = self.new_value.get()
            modify_type = self.modify_type.get()

            # Store original value if not already stored
            if self.selected_result['selector'] not in self.original_values:
                self.original_values[self.selected_result['selector']] = self.current_value.get()

            # Apply modification
            if modify_type == "Text":
                self.driver.execute_script("arguments[0].textContent = arguments[1];", element, new_value)
            elif modify_type == "HTML":
                self.driver.execute_script("arguments[0].innerHTML = arguments[1];", element, new_value)
            elif modify_type == "Attribute":
                attr_name = self.attribute_name.get()
                if not attr_name:
                    messagebox.showwarning("No Attribute", "Please specify an attribute name")
                    return
                self.driver.execute_script(f"arguments[0].setAttribute('{attr_name}', arguments[1]);", element, new_value)
            elif modify_type == "Value":
                self.driver.execute_script("arguments[0].value = arguments[1];", element, new_value)

            self.log_message(f"Applied changes to element: {new_value}", "SUCCESS")
            self.current_value.delete(0, tk.END)
            self.current_value.insert(0, new_value)

        except Exception as e:
            self.log_message(f"Failed to apply changes: {str(e)}", "ERROR")
            messagebox.showerror("Error", f"Failed to apply changes: {str(e)}")

    def freeze_value(self):
        """Freeze the current value of the selected element"""
        if not hasattr(self, 'selected_result') or self.selected_result is None:
            messagebox.showwarning("No Selection", "Please select an element first")
            return

        try:
            element = self.selected_result['element']
            current_value = element.text

            # Start a thread to continuously set the value
            freeze_thread = threading.Thread(target=self.freeze_value_worker, args=(element, current_value))
            freeze_thread.daemon = True
            freeze_thread.start()

            self.log_message(f"Freezing value: {current_value}", "SUCCESS")

        except Exception as e:
            self.log_message(f"Failed to freeze value: {str(e)}", "ERROR")

    def freeze_value_worker(self, element, value):
        """Worker thread to freeze a value"""
        while True:
            try:
                self.driver.execute_script("arguments[0].textContent = arguments[1];", element, value)
                time.sleep(0.1)
            except Exception:
                break

    def reset_value(self):
        """Reset the selected element to its original value"""
        if not hasattr(self, 'selected_result') or self.selected_result is None:
            messagebox.showwarning("No Selection", "Please select an element first")
            return

        try:
            selector = self.selected_result['selector']
            if selector in self.original_values:
                original = self.original_values[selector]
                element = self.selected_result['element']

                self.driver.execute_script("arguments[0].textContent = arguments[1];", element, original)
                self.current_value.delete(0, tk.END)
                self.current_value.insert(0, original)

                self.log_message(f"Reset to original value: {original}", "SUCCESS")
            else:
                messagebox.showinfo("No Original", "No original value stored for this element")

        except Exception as e:
            self.log_message(f"Failed to reset value: {str(e)}", "ERROR")

    def save_snapshot(self):
        """Save a snapshot of the current page state"""
        if not self.driver:
            messagebox.showwarning("No Browser", "Please connect to a browser first")
            return

        try:
            snapshot = {
                'url': self.driver.current_url,
                'html': self.driver.page_source,
                'timestamp': time.time()
            }

            # Save to file
            filename = f"snapshot_{int(time.time())}.json"
            with open(filename, 'w') as f:
                json.dump(snapshot, f, indent=2)

            self.log_message(f"Snapshot saved to {filename}", "SUCCESS")

        except Exception as e:
            self.log_message(f"Failed to save snapshot: {str(e)}", "ERROR")

    def toggle_monitoring(self):
        """Toggle the value monitoring feature"""
        if self.monitor_var.get():
            # Start monitoring
            self.monitor_thread = threading.Thread(target=self.monitor_values)
            self.monitor_thread.daemon = True
            self.monitor_thread.start()
            self.log_message("Value monitoring started", "SUCCESS")
        else:
            self.log_message("Value monitoring stopped", "INFO")

    def monitor_values(self):
        """Monitor values and log changes"""
        last_values = {}

        while self.monitor_var.get():
            try:
                if self.driver and self.scan_results:
                    for result in self.scan_results:
                        try:
                            element = result['element']
                            current_value = element.text
                            selector = result['selector']

                            if selector in last_values:
                                if last_values[selector] != current_value:
                                    self.monitor_display.insert(
                                        tk.END,
                                        f"[{time.strftime('%H:%M:%S')}] Value changed for {selector}:\n"
                                    )
                                    self.monitor_display.insert(tk.END, f"  Old: {last_values[selector]}\n")
                                    self.monitor_display.insert(tk.END, f"  New: {current_value}\n\n")
                                    self.monitor_display.see(tk.END)

                            last_values[selector] = current_value

                        except StaleElementReferenceException:
                            continue

                interval = int(self.poll_interval.get())
                time.sleep(interval / 1000.0)

            except Exception as e:
                self.log_message(f"Monitoring error: {str(e)}", "ERROR")
                break


def main():
    """Main entry point"""
    root = tk.Tk()
    WebCheatEngine(root)
    root.mainloop()


if __name__ == "__main__":
    main()

