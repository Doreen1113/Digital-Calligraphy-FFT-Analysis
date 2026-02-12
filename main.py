import argparse
import os
import sys
import subprocess


def run_gui(init_coeffs: int = 50):
    # Start the PyQt GUI in-process so `py main.py` directly opens the window
    try:
        from PyQt5.QtWidgets import QApplication
        from GUI import InteractiveWindow
    except Exception as e:
        print("Failed to import GUI dependencies:", e)
        return 2

    app = QApplication(sys.argv)
    tool = InteractiveWindow(init_coeffs=init_coeffs)
    tool.show()
    return app.exec()


def run_svg(svg_path: str, n_coeffs: int = None, user_scale: float = 1.0):
    from fft import draw

    if not os.path.exists(svg_path):
        print(f"SVG not found: {svg_path}")
        return 2
    draw(svg_path, n_coeffs=n_coeffs, user_scale=user_scale)
    return 0


def main():
    parser = argparse.ArgumentParser(description="Unified entry for Fourier_drawing project")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--gui", action="store_true", help="Start the PyQt GUI")
    group.add_argument("--svg", metavar="PATH", help="Run fft.draw on given SVG file")
    parser.add_argument("--coeffs", type=int, default=50, help="Number of Fourier coefficients to keep (low-pass).")
    parser.add_argument("--scale", type=float, default=1.0, help="User scale multiplier (e.g. 1.0 = 100%)")

    args = parser.parse_args()

    if args.gui:
        return run_gui(init_coeffs=args.coeffs)
    if args.svg:
        return run_svg(args.svg, n_coeffs=args.coeffs, user_scale=args.scale)

    # default: start GUI with CLI coeffs
    return run_gui(init_coeffs=args.coeffs)


if __name__ == "__main__":
    sys.exit(main())
