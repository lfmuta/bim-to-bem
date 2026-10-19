import sys
import logging
from pathlib import Path
import pandas as pd

# --- Configuration ---
BIOCLIMATIC_ZONE = "3A e 3B" # USER: Change this value to your bioclimatic zone (ABNT NBR 15220-3): "1R e 1M", "2R e 2M", "3A e 3B", "4A e 4B", "5A e 5B" or "6A e 6B"
TYPOLOGY = "Educacionais"

# --- Constants ---
BIOCLIMATIC_ZONES = ["1R e 1M", "2R e 2M", "3A e 3B", "4A e 4B", "5A e 5B", "6A e 6B"]

# CRCEPD-A Table 8.3 (Tipologia vs Zona Bioclimática)
CRCEPD_A_TABLE = {
    "Educacionais": {"1R e 1M": 0.56, "2R e 2M": 0.48, "3A e 3B": 0.51, "4A e 4B": 0.43, "5A e 5B": 0.33, "6A e 6B": 0.32}
}

# CRCgTTD-A Table 8.5 (Tipologia vs Zona Bioclimática)
CRCGTT_D_A_TABLE = {
    "Educacionais": {"1R e 1M": 0.25, "2R e 2M": 0.18, "3A e 3B": 0.15, "4A e 4B": 0.09, "5A e 5B": 0.07, "6A e 6B": 0.07}
}

# --- Utility Functions ---
def setup_logging(output_dir: Path):
    """
    Sets up logging to save detailed execution information to a log file.
    """
    log_file = output_dir / "crcepd_a_calculation.log"
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, mode='w', encoding='utf-8'),
        ]
    )
    return logging.getLogger(__name__)

def calculate_crcepd_a(bioclimatic_zone: str, typology: str = TYPOLOGY, logger=None) -> float:
    """
    Returns CRCEPD-A from Table 8.3 according to typology and bioclimatic zone.
    """
    if typology not in CRCEPD_A_TABLE:
        raise ValueError(f"Invalid typology: {typology}")
    if bioclimatic_zone not in CRCEPD_A_TABLE[typology]:
        raise ValueError(f"Invalid bioclimatic zone: {bioclimatic_zone}. Valid zones: {', '.join(BIOCLIMATIC_ZONES)}")
    crcepd_a = CRCEPD_A_TABLE[typology][bioclimatic_zone]
    if logger:
        logger.info(f"Typology={typology}, Bioclimatic Zone={bioclimatic_zone} -> CRCEPD-A = {crcepd_a}")
    return crcepd_a

def calculate_crcgtt_d_a(bioclimatic_zone: str, typology: str = TYPOLOGY, logger=None) -> float:
    """
    Returns CRCgTTD-A from Table 8.5 according to typology and bioclimatic zone.
    """
    if bioclimatic_zone not in CRCGTT_D_A_TABLE[typology]:
        raise ValueError(f"Invalid bioclimatic zone: {bioclimatic_zone}. Valid zones: {', '.join(BIOCLIMATIC_ZONES)}")
    crcgtt = CRCGTT_D_A_TABLE[typology][bioclimatic_zone]
    if logger:
        logger.info(f"Typology={typology}, Bioclimatic Zone={bioclimatic_zone} -> CRCgTTD-A = {crcgtt}")
    return crcgtt

def calculate_factor_i(coefficient: float, logger=None) -> float:
    """
    Calculates factor i (Equations 8.8 and 8.9).
    Formula: i = (coefficient * 100) / 3
    """
    factor_i = (coefficient * 100) / 3
    if logger:
        logger.info(f"Calculating factor i: ({coefficient:.4f} * 100) / 3 = {factor_i:.4f}")
    return factor_i

def calculate_class(reduction: float, factor_i: float) -> str:
    """
    Returns the efficiency class (Tables 8.2 and 8.4).
    """
    if reduction < 0:
        return "E"
    if reduction <= factor_i:
        return "D"
    if reduction <= 2 * factor_i:
        return "C"
    if reduction <= 3 * factor_i:
        return "B"
    return "A"

def calculate_coefficients(bioclimatic_zone: str, typology: str = TYPOLOGY, logger=None) -> dict:
    """
    Calculates CRCEPD-A, CRCgTTD-A and the corresponding factors i.
    """
    crcepd_a = calculate_crcepd_a(bioclimatic_zone, typology, logger)
    crcgtt = calculate_crcgtt_d_a(bioclimatic_zone, typology, logger)
    return {
        'bioclimatic_zone': bioclimatic_zone,
        'typology': typology,
        'crcepd_a': crcepd_a,
        'factor_i': calculate_factor_i(crcepd_a, logger),
        'crcgtt_d_a': crcgtt,
        'factor_i_envelope': calculate_factor_i(crcgtt, logger)
    }

def main():
    """
    Main function to execute the CRCEPD-A, CRCgTTD-A and factor i calculation script.
    """
    try:
        zone = sys.argv[1] if len(sys.argv) > 1 else BIOCLIMATIC_ZONE
        output_dir = Path.cwd()
        logger = setup_logging(output_dir)
        print("=== INI-C CRCEPD-A, CRCgTTD-A and Factor i Calculator ===\n")
        print(f"Typology: {TYPOLOGY}")
        print(f"Bioclimatic Zone: {zone}")
        print("(To change the bioclimatic zone, edit BIOCLIMATIC_ZONE or pass it as argument, e.g. python 14_b_crcepd-a.py \"3A e 3B\")\n")

        results = calculate_coefficients(zone, TYPOLOGY, logger)

        print(f"\n" + "="*70)
        print(f" CALCULATION RESULTS")
        print(f"="*70)
        print(f" CRCEPD-A (Table 8.3) = {results['crcepd_a']:.2f}")
        print(f" Factor i (general classification) = {results['factor_i']:.4f}")
        print(f" CRCgTTD-A (Table 8.5) = {results['crcgtt_d_a']:.2f}")
        print(f" Factor i (envelope) = {results['factor_i_envelope']:.4f}")
        print(f"="*70)

        summary_data = {
            'Metric': ['Typology', 'Bioclimatic Zone', 'CRCEPD-A', 'Factor i', 'CRCgTTD-A', 'Factor i envelope'],
            'Value': [results['typology'], results['bioclimatic_zone'], results['crcepd_a'], results['factor_i'], results['crcgtt_d_a'], results['factor_i_envelope']]
        }
        summary_file = output_dir / "crcepd_a_summary.csv"
        pd.DataFrame(summary_data).to_csv(summary_file, index=False)
        print(f"\nSummary results saved to: {summary_file}")

    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
