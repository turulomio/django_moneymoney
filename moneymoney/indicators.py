"""
    This module uses a dataframe with date, open, close, high, low and adds indicators values
"""

import pandas as pd
import numpy as np
def sma(df, period):
    """
        Returns dataframe with new key SMA{period}
    """

    df[f'SMA{period}'] = df['close'].rolling(window=period).mean()
    return df

def hma(df, period):
    """
        Calcula la Media Móvil de Hull (HMA) de manera eficiente usando pandas.

        Args:
            data_dicts (list): Una lista de diccionarios, cada uno con una clave 'date' (datetime) y 'value'.
            period (int): El período para la HMA.

        Returns:
            pandas.DataFrame: Un DataFrame con la fecha, el valor original y la HMA calculada.
    """
    if not isinstance(period, int) or period <= 1:
        raise ValueError("El período debe ser un entero mayor que 1.")

    # # 1. Convertir la lista de diccionarios a un DataFrame
    # # Esta parte funciona perfectamente con objetos datetime.
    # df['date'] = pd.to_datetime(df['date']) # Asegura el tipo de dato, aunque ya sea datetime
    # df.set_index('date', inplace=True)



    # Definir la función para la Media Móvil Ponderada (WMA)
    def wma(series):
        weights = np.arange(1, len(series) + 1)
        return np.dot(series, weights) / weights.sum()

    # 2. Calcular las dos WMAs iniciales
    half_period = int(period / 2)
    sqrt_period = int(np.sqrt(period))

    wma_half = df['close'].rolling(window=half_period).apply(wma, raw=True)
    wma_full = df['close'].rolling(window=period).apply(wma, raw=True)

    # 3. Crear la serie de diferencias
    df['diff'] = 2 * wma_half - wma_full

    # 4. Calcular la HMA final sobre la serie de diferencias
    df[f'HMA{period}'] = df['diff'].rolling(window=sqrt_period).apply(wma, raw=True)

    df.dropna().reset_index()#.to_dict(orient="records")
    # 2. Remove the 'diff' column directly from the DataFrame
    df.drop(columns='diff', inplace=True)
    return df