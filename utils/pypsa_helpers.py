
# utils/pypsa_helpers.py
import pandas as pd
import numpy_financial as npf
import numpy as np
import logging

# It's good practice to get a logger instance rather than using the root logger directly
# if this module might be imported elsewhere.
logger = logging.getLogger(__name__) # Use module's own logger

def find_special_symbols(df, marker):
    """Finds cells starting with a specific marker string."""
    markers = []
    for i, row in df.iterrows():
        for j, value in enumerate(row):
            if isinstance(value, str) and value.startswith(marker):
                # Ensure the actual table name is captured, not just the marker
                table_name = value[len(marker):].strip()
                if table_name: # Only add if there's a name after the marker
                    markers.append((i, j, table_name))
    return markers

def extract_table(df, start_row_data, start_col_data):
    """
    Extracts a table from a DataFrame starting at given data cell (after header and marker).
    The header is assumed to be at (start_row_data - 1, start_col_data).
    """
    header_row_idx = start_row_data - 1
    if header_row_idx < 0:
        logger.warning(f"Header row index ({header_row_idx}) is invalid. Cannot extract table.")
        return pd.DataFrame()

    # Determine end_row by finding first empty cell in the first column of the data block
    end_row_data = start_row_data
    while end_row_data < len(df) and pd.notnull(df.iloc[end_row_data, start_col_data]):
        end_row_data += 1

    # Determine end_col by finding first empty cell in the header row
    end_col_data = start_col_data
    # Check header row (header_row_idx) for end of columns
    while end_col_data < len(df.columns) and pd.notnull(df.iloc[header_row_idx, end_col_data]):
        end_col_data += 1

    if start_row_data >= end_row_data or start_col_data >= end_col_data:
        logger.warning(f"Table dimensions invalid or no data found at ({start_row_data}, {start_col_data}).")
        return pd.DataFrame()

    # Extract data, set header, and reset index
    table_content = df.iloc[start_row_data:end_row_data, start_col_data:end_col_data].copy()
    header_content = df.iloc[header_row_idx, start_col_data:end_col_data].copy()
    
    if header_content.empty or table_content.empty:
        logger.warning(f"No header or table data extracted for table at ({start_row_data-1}, {start_col_data}).")
        return pd.DataFrame()
        
    table_content.columns = header_content
    table_content.reset_index(drop=True, inplace=True)
    return table_content


def extract_tables_by_markers(df, marker_prefix):
    """
    Extracts multiple tables from a DataFrame, identified by cells starting with marker_prefix.
    Example: marker_prefix='~', finds '~TableName1', '~TableName2'.
    """
    table_markers_info = find_special_symbols(df, marker_prefix)
    tables = {}
    for r_marker, c_marker, table_name in table_markers_info:
        # Data table starts on the row after the header row, which is row after marker row.
        # Header is at (r_marker + 1, c_marker). Data starts at (r_marker + 2, c_marker).
        logger.info(f"Attempting to extract table '{table_name}' marked at ({r_marker},{c_marker}). Header expected at ({r_marker+1},{c_marker}). Data from ({r_marker+2},{c_marker}).")
        
        # Pass the starting row and column of the *data itself* to extract_table
        # Header is assumed to be one row above that.
        # Marker at (r_marker, c_marker)
        # Header at (r_marker + 1, c_marker)
        # Data starts at (r_marker + 2, c_marker)
        
        # Check if there's space for header and at least one data row
        if r_marker + 2 < len(df):
            extracted_df = extract_table(df, r_marker + 2, c_marker)
            if not extracted_df.empty:
                tables[table_name] = extracted_df
                logger.info(f"Successfully extracted table '{table_name}' with {len(extracted_df)} rows and {len(extracted_df.columns)} columns.")
            else:
                logger.warning(f"Extraction for table '{table_name}' (marked at {r_marker},{c_marker}) resulted in an empty DataFrame.")
        else:
            logger.warning(f"Not enough rows for header/data for table '{table_name}' marked at ({r_marker},{c_marker}).")
    return tables


def annuity_future_value(rate, nper, pv):
    """Calculates the annuity (payment) for a present value (pv)."""
    if pd.isna(rate) or pd.isna(nper) or pd.isna(pv):
        logger.warning(f"NaN input to annuity: rate={rate}, nper={nper}, pv={pv}. Returning 0.")
        return 0
    if nper <= 0: # Number of periods must be positive
        logger.warning(f"Non-positive nper ({nper}) for annuity calculation with pv={pv}. Returning 0.")
        return 0
    if rate == 0: # Special case for 0 interest rate
        # If rate is 0, pmt is simply pv spread over nper
        # npf.pmt handles this, but good to be aware.
        # If pv is cost (negative), pmt is positive payment.
        # If pv is loan (positive), pmt is negative payment.
        # The formula pv = pmt * nper implies pmt = pv / nper.
        # Given pv is usually cost (e.g. -1000), pmt should be positive.
        # npf.pmt(0, 10, -1000) = 100. So, -pv/nper if pv is positive cost.
        # If pv is defined as a positive cost, then pmt = pv/nper.
        # The provided notebook uses abs(npf.pmt(...)) for capital_cost, so pv is likely positive.
        # Let's assume pv is a positive value representing the initial cost.
        # Then the payment to amortize it would be pv/nper.
        # npf.pmt(0.0, 10, 1000) returns -100.
        # So npf.pmt correctly handles pv as "present value of loan" sense.
        # If our 'pv' is an investment cost, we should pass it as positive if we expect a negative pmt,
        # or negative if we expect a positive pmt.
        # The notebook passes positive capital_cost_df value as pv.
        # abs(annuity_future_value(...)) is used.
        # Let's keep it consistent with npf.pmt's sign convention.
        pass # npf.pmt handles rate = 0

    try:
        # npf.pmt calculates payment for a loan (pv positive, pmt negative)
        # or investment (pv negative, pmt positive).
        # If pv is an upfront cost (positive), pmt will be negative (payments made).
        pmt_val = npf.pmt(float(rate), float(nper), float(pv), fv=0, when='end')
        logger.debug(f"Calculated annuity: rate={rate}, nper={nper}, pv={pv} -> pmt={pmt_val}")
        return pmt_val # Return with its natural sign
    except Exception as e:
        logger.error(f"Error in npf.pmt with rate={rate}, nper={nper}, pv={pv}: {e}", exc_info=True)
        return 0 # Or np.nan, or raise error, depending on desired behavior for failure
