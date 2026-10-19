import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import font as tkFont

def calculate_energy_class(prpec: float, factor_i: float) -> str:
    """
    Calculates the energy performance class based on PRPEC and factor i.
    """
    if prpec < 0:
        return "E"
    elif prpec >= 0 and prpec <= factor_i:
        return "D"
    elif prpec > factor_i and prpec <= 2 * factor_i:
        return "C"
    elif prpec > 2 * factor_i and prpec <= 3 * factor_i:
        return "B"
    else: # prpec > 3 * factor_i
        return "A"

def get_class_colors() -> dict:
    """
    Returns color information for each class.
    """
    return {
        "A": {"bg": "#00A651", "fg": "white"},
        "B": {"bg": "#8CC63F", "fg": "white"},
        "C": {"bg": "#FFF200", "fg": "white"},
        "D": {"bg": "#FF9E1B", "fg": "white"},
        "E": {"bg": "#ED1C24", "fg": "white"}
    }

class EnergyLabelGenerator:
    def __init__(self, root):
        self.root = root
        self.root.title("Energy Performance Label Generator")
        self.root.geometry("650x750")
        self.root.resizable(True, True)
        self.root.configure(bg='#F5F7FA')
        self.setup_styles()
        self.create_input_interface()

    def setup_styles(self):
        """Setup fonts and styles."""
        self.title_font = tkFont.Font(family="Segoe UI", size=22, weight="bold")
        self.subtitle_font = tkFont.Font(family="Segoe UI", size=10)
        self.label_font = tkFont.Font(family="Segoe UI", size=11)
        self.entry_font = tkFont.Font(family="Segoe UI", size=11)
        self.button_font = tkFont.Font(family="Segoe UI", size=13, weight="bold")

    def create_input_interface(self):
        """Create the input interface with scrollbar."""
        # Main container
        main_container = tk.Frame(self.root, bg='#F5F7FA')
        main_container.pack(fill=tk.BOTH, expand=True)

        # Header (fixed at top)
        header_frame = tk.Frame(main_container, bg='#F5F7FA')
        header_frame.pack(fill=tk.X, padx=40, pady=(30, 0))

        tk.Label(
            header_frame,
            text="Energy Performance Label",
            font=self.title_font,
            bg='#F5F7FA',
            fg='#2C3E50'
        ).pack(pady=(0, 5))

        tk.Label(
            header_frame,
            text="Enter building performance metrics",
            font=self.subtitle_font,
            bg='#F5F7FA',
            fg='#7F8C8D'
        ).pack(pady=(0, 20))

        # Create canvas and scrollbar for scrollable content
        canvas_frame = tk.Frame(main_container, bg='#F5F7FA')
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=40)

        canvas = tk.Canvas(canvas_frame, bg='#F5F7FA', highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#F5F7FA')

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Input card
        input_card = tk.Frame(scrollable_frame, bg='white')
        input_card.pack(fill=tk.BOTH, pady=(0, 20))

        input_inner = tk.Frame(input_card, bg='white')
        input_inner.pack(fill=tk.BOTH, padx=30, pady=30)

        # Classification Metrics Section
        tk.Label(
            input_inner,
            text="CLASSIFICATION METRICS",
            font=tkFont.Font(family="Segoe UI", size=10, weight="bold"),
            bg='white',
            fg='#7F8C8D'
        ).pack(anchor='w', pady=(0, 15))

        # PRPEC
        self.prpec_var = tk.StringVar()
        self.create_input_field(input_inner, "PRPEC (%)", self.prpec_var)

        # Factor i
        self.factor_i_var = tk.StringVar()
        self.create_input_field(input_inner, "Factor i", self.factor_i_var)

        # Divider
        tk.Frame(input_inner, bg='#ECF0F1', height=1).pack(fill=tk.X, pady=20)

        # Energy Use Intensity Section
        tk.Label(
            input_inner,
            text="ENERGY USE INTENSITY (EUI)",
            font=tkFont.Font(family="Segoe UI", size=10, weight="bold"),
            bg='white',
            fg='#7F8C8D'
        ).pack(anchor='w', pady=(0, 15))

        # Cooling EUI
        self.cooling_eui_var = tk.StringVar()
        self.create_input_field(input_inner, "Cooling EUI (kWh/m²/year)", self.cooling_eui_var)

        # Lighting EUI
        self.lighting_eui_var = tk.StringVar()
        self.create_input_field(input_inner, "Lighting EUI (kWh/m²/year)", self.lighting_eui_var)

        # Equipment EUI
        self.equipment_eui_var = tk.StringVar()
        self.create_input_field(input_inner, "Equipment EUI (kWh/m²/year)", self.equipment_eui_var)

        # Total EUI
        self.total_eui_var = tk.StringVar()
        self.create_input_field(input_inner, "Total EUI (kWh/m²/year)", self.total_eui_var)

        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Enable mousewheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # Button frame (fixed at bottom)
        button_frame = tk.Frame(main_container, bg='#F5F7FA')
        button_frame.pack(fill=tk.X, padx=40, pady=(10, 30))

        generate_btn = tk.Button(
            button_frame,
            text="Generate Energy Performance Label",
            command=self.generate_label,
            font=self.button_font,
            bg='#3498DB',
            fg='white',
            activebackground='#2980B9',
            activeforeground='white',
            relief=tk.FLAT,
            cursor='hand2',
            padx=30,
            pady=15
        )
        generate_btn.pack()

        generate_btn.bind('<Enter>', lambda e: generate_btn.config(bg='#2980B9'))
        generate_btn.bind('<Leave>', lambda e: generate_btn.config(bg='#3498DB'))

    def create_input_field(self, parent, label_text, variable):
        """Create an input field."""
        field_frame = tk.Frame(parent, bg='white')
        field_frame.pack(fill=tk.X, pady=(0, 12))

        tk.Label(
            field_frame,
            text=label_text,
            font=self.label_font,
            bg='white',
            fg='#34495E'
        ).pack(anchor='w', pady=(0, 5))

        entry_bg = tk.Frame(field_frame, bg='#ECF0F1')
        entry_bg.pack(fill=tk.X)

        entry = tk.Entry(
            entry_bg,
            textvariable=variable,
            font=self.entry_font,
            bg='#ECF0F1',
            fg='#2C3E50',
            relief=tk.FLAT,
            insertbackground='#3498DB'
        )
        entry.pack(fill=tk.X, padx=10, pady=8)

    def generate_label(self):
        """Generate and display the energy performance label."""
        try:
            # Get and validate inputs
            prpec_text = self.prpec_var.get().strip()
            factor_i_text = self.factor_i_var.get().strip()
            cooling_eui_text = self.cooling_eui_var.get().strip()
            lighting_eui_text = self.lighting_eui_var.get().strip()
            equipment_eui_text = self.equipment_eui_var.get().strip()
            total_eui_text = self.total_eui_var.get().strip()

            # Check if all fields are filled
            if not all([prpec_text, factor_i_text, cooling_eui_text,
                       lighting_eui_text, equipment_eui_text, total_eui_text]):
                messagebox.showerror("Input Error", "Please fill in all fields.")
                return

            prpec = float(prpec_text.replace(',', '.'))
            factor_i = float(factor_i_text.replace(',', '.'))
            cooling_eui = float(cooling_eui_text.replace(',', '.'))
            lighting_eui = float(lighting_eui_text.replace(',', '.'))
            equipment_eui = float(equipment_eui_text.replace(',', '.'))
            total_eui = float(total_eui_text.replace(',', '.'))

            if factor_i <= 0:
                messagebox.showerror("Input Error", "Factor i must be greater than zero.")
                return

            # Calculate class
            energy_class = calculate_energy_class(prpec, factor_i)

            # Create label window
            self.show_energy_label(energy_class, prpec,
                                  cooling_eui, lighting_eui, equipment_eui, total_eui)

        except ValueError:
            messagebox.showerror("Input Error", "Please enter valid numeric values in all fields.")
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {str(e)}")

    def show_energy_label(self, energy_class, prpec, cooling_eui, lighting_eui, equipment_eui, total_eui):
        """Display the energy performance label in a new window (LANDSCAPE)."""
        label_window = tk.Toplevel(self.root)
        label_window.title("Energy Performance Label")
        label_window.geometry("1100x700") # Landscape
        label_window.resizable(True, True)
        label_window.configure(bg='white')

        # Create canvas with scrollbar
        canvas = tk.Canvas(label_window, bg='white', highlightthickness=0)
        scrollbar = ttk.Scrollbar(label_window, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='white')

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw", width=1100)
        canvas.configure(yscrollcommand=scrollbar.set)

        # Main container
        main_container = tk.Frame(scrollable_frame, bg='white')
        main_container.pack(fill=tk.BOTH, expand=True, padx=50, pady=40)

        # ===== HEADER SECTION =====
        header_frame = tk.Frame(main_container, bg='#2C3E50', relief=tk.FLAT)
        header_frame.pack(fill=tk.X, pady=(0, 40))

        header_inner = tk.Frame(header_frame, bg='#2C3E50')
        header_inner.pack(fill=tk.X, padx=30, pady=25)

        tk.Label(
            header_inner,
            text="ENERGY PERFORMANCE LABEL",
            font=tkFont.Font(family="Segoe UI", size=20, weight="bold"),
            bg='#2C3E50',
            fg='white'
        ).pack(pady=(0, 8))

        tk.Label(
            header_inner,
            text="Commercial, Service and Public Buildings",
            font=tkFont.Font(family="Segoe UI", size=11),
            bg='#2C3E50',
            fg='#BDC3C7'
        ).pack(pady=(0, 12))

        tk.Label(
            header_inner,
            text="Brazilian Building Labeling Program • Ordinance No. 309/2022",
            font=tkFont.Font(family="Segoe UI", size=9),
            bg='#2C3E50',
            fg='#95A5A6'
        ).pack()

        # ===== MAIN CONTENT: TWO COLUMNS =====
        content_frame = tk.Frame(main_container, bg='white')
        content_frame.pack(fill=tk.BOTH, expand=True)

        # LEFT COLUMN: Staggered bars (left-aligned)
        left_column = tk.Frame(content_frame, bg='white')
        left_column.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 40))

        self.create_staggered_bars(left_column, energy_class)

        # RIGHT COLUMN: Classification + EUI metrics
        right_column = tk.Frame(content_frame, bg='white')
        right_column.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Classification display
        self.create_classification_box(right_column, energy_class, prpec)

        # Spacer
        tk.Frame(right_column, bg='white', height=30).pack()

        # EUI Section
        self.create_eui_section(right_column, cooling_eui, lighting_eui, equipment_eui, total_eui)

        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Enable mousewheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        label_window.bind_all("<MouseWheel>", _on_mousewheel)

    def create_staggered_bars(self, parent, current_class):
        """Create staggered arrow bars - all left-aligned, increasing width from A to E."""
        bars_container = tk.Frame(parent, bg='white')
        bars_container.pack(expand=True)

        classes = ['A', 'B', 'C', 'D', 'E']
        colors = get_class_colors()

        # Widths: A smallest (180px), E largest (380px)
        widths = [180, 230, 280, 330, 380]
        height = 65
        arrow_width = 20  # Width of the arrow point

        for idx, cls in enumerate(classes):
            color_info = colors[cls]

            # Container for each bar (left-aligned)
            bar_container = tk.Frame(bars_container, bg='white')
            bar_container.pack(anchor='w', pady=3)

            # Create canvas for arrow shape
            canvas = tk.Canvas(
                bar_container,
                width=widths[idx],
                height=height,
                bg='white',
                highlightthickness=0
            )
            canvas.pack(side=tk.LEFT)

            # Draw arrow polygon (pointing right)
            # Points: top-left, top-right-inner, arrow-tip, bottom-right-inner, bottom-left
            points = [
                0, 0,  # top-left
                widths[idx] - arrow_width, 0,  # top-right-inner
                widths[idx], height / 2,  # arrow tip (right point)
                widths[idx] - arrow_width, height,  # bottom-right-inner
                0, height  # bottom-left
            ]

            canvas.create_polygon(
                points,
                fill=color_info['bg'],
                outline=color_info['bg']
            )

            # Add text (left-aligned with padding)
            canvas.create_text(
                20,  # Left padding
                height / 2,
                text=cls,
                font=tkFont.Font(family="Segoe UI", size=28, weight="bold"),
                fill=color_info['fg'],
                anchor='w'
            )

    def create_classification_box(self, parent, energy_class, prpec):
        """Create the classification display box."""
        box_frame = tk.Frame(parent, bg='#F8F9FA', relief=tk.FLAT)
        box_frame.pack(fill=tk.X)

        box_inner = tk.Frame(box_frame, bg='#F8F9FA')
        box_inner.pack(padx=30, pady=30)

        tk.Label(
            box_inner,
            text="BUILDING CLASSIFICATION",
            font=tkFont.Font(family="Segoe UI", size=11, weight="bold"),
            bg='#F8F9FA',
            fg='#7F8C8D'
        ).pack(pady=(0, 20))

        # Class badge
        color_info = get_class_colors()[energy_class]
        badge = tk.Frame(box_inner, bg=color_info['bg'], width=140, height=140, relief=tk.FLAT)
        badge.pack_propagate(False)
        badge.pack(pady=(0, 20))

        tk.Label(
            badge,
            text=energy_class,
            font=tkFont.Font(family="Segoe UI", size=72, weight="bold"),
            bg=color_info['bg'],
            fg=color_info['fg']
        ).place(relx=0.5, rely=0.5, anchor='center')

        # PRPEC value
        prpec_frame = tk.Frame(box_inner, bg='#E8F5E9', relief=tk.FLAT)
        prpec_frame.pack(fill=tk.X)

        prpec_inner = tk.Frame(prpec_frame, bg='#E8F5E9')
        prpec_inner.pack(padx=20, pady=15)

        tk.Label(
            prpec_inner,
            text="PRPEC",
            font=tkFont.Font(family="Segoe UI", size=9),
            bg='#E8F5E9',
            fg='#5D6D7E'
        ).pack()

        tk.Label(
            prpec_inner,
            text=f"{prpec:.2f}%",
            font=tkFont.Font(family="Segoe UI", size=20, weight="bold"),
            bg='#E8F5E9',
            fg='#2C3E50'
        ).pack(pady=(5, 0))

    def create_eui_section(self, parent, cooling_eui, lighting_eui, equipment_eui, total_eui):
        """Create the EUI metrics section."""
        eui_frame = tk.Frame(parent, bg='white', relief=tk.FLAT)
        eui_frame.pack(fill=tk.BOTH, expand=True)

        # Header
        header = tk.Frame(eui_frame, bg='#ECF0F1', relief=tk.FLAT)
        header.pack(fill=tk.X, pady=(0, 20))

        tk.Label(
            header,
            text="ENERGY USE INTENSITY",
            font=tkFont.Font(family="Segoe UI", size=11, weight="bold"),
            bg='#ECF0F1',
            fg='#2C3E50',
            pady=12
        ).pack()

        # Calculate percentages
        cooling_pct = (cooling_eui / total_eui * 100) if total_eui > 0 else 0
        lighting_pct = (lighting_eui / total_eui * 100) if total_eui > 0 else 0
        equipment_pct = (equipment_eui / total_eui * 100) if total_eui > 0 else 0

        # EUI bars
        self.create_eui_bar(eui_frame, "COOLING", cooling_eui, cooling_pct, "#4FC3F7", total_eui)
        self.create_eui_bar(eui_frame, "LIGHTING", lighting_eui, lighting_pct, "#FFD54F", total_eui)
        self.create_eui_bar(eui_frame, "EQUIPMENT", equipment_eui, equipment_pct, "#FF8A65", total_eui)

        # Total
        total_frame = tk.Frame(eui_frame, bg='#1565C0', relief=tk.FLAT)
        total_frame.pack(fill=tk.X, pady=(15, 0))

        total_inner = tk.Frame(total_frame, bg='#1565C0')
        total_inner.pack(padx=20, pady=18)

        tk.Label(
            total_inner,
            text="TOTAL EUI",
            font=tkFont.Font(family="Segoe UI", size=10, weight="bold"),
            bg='#1565C0',
            fg='white'
        ).pack(side=tk.LEFT)

        tk.Label(
            total_inner,
            text=f"{total_eui:.2f} kWh/m²/year",
            font=tkFont.Font(family="Segoe UI", size=14, weight="bold"),
            bg='#1565C0',
            fg='white'
        ).pack(side=tk.RIGHT)

    def create_eui_bar(self, parent, label, value, percentage, color, total):
        """Create an EUI bar with percentage on the side."""
        container = tk.Frame(parent, bg='white', relief=tk.FLAT)
        container.pack(fill=tk.X, pady=(0, 15))

        # Label row with percentage on the side
        label_row = tk.Frame(container, bg='white')
        label_row.pack(fill=tk.X, pady=(0, 8))

        tk.Label(
            label_row,
            text=f"{label} - {percentage:.1f}%",
            font=tkFont.Font(family="Segoe UI", size=10, weight="bold"),
            bg='white',
            fg='#34495E'
        ).pack(side=tk.LEFT)

        tk.Label(
            label_row,
            text=f"{value:.2f} kWh/m²/year",
            font=tkFont.Font(family="Segoe UI", size=10),
            bg='white',
            fg='#7F8C8D'
        ).pack(side=tk.RIGHT)

        # Progress bar (no border, flat)
        bar_bg = tk.Frame(container, bg='#E8E8E8', height=28, relief=tk.FLAT)
        bar_bg.pack(fill=tk.X)

        if total > 0:
            bar_width_percent = value / total
        else:
            bar_width_percent = 0

        bar_fill = tk.Frame(bar_bg, bg=color, height=28, relief=tk.FLAT)
        bar_fill.place(relx=0, rely=0, relwidth=bar_width_percent, relheight=1)

def main():
    """Main function."""
    root = tk.Tk()
    app = EnergyLabelGenerator(root)

    # Center window
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f"{width}x{height}+{x}+{y}")

    root.mainloop()

if __name__ == "__main__":
    main()
