import streamlit as st
import yfinance as yf
import pandas as pd
import mplfinance as mpf
from datetime import datetime, timedelta

def load_data( ticker_symbol, start_date, end_date ):
    """Load and clean stock data from Yahoo Finance."""
    try:
        # Create a Ticker object
        ticker = yf.Ticker( ticker_symbol )
        
        # Download historical data
        stock_data = ticker.history(
            start = start_date,
            end = end_date,
            interval = "1d"
        )
        
        if stock_data.empty:
            return pd.DataFrame()
        
        # Clean and convert data types
        stock_data = stock_data.copy()
        
        # Convert price columns to float
        for column in [ "Open", "High", "Low", "Close" ]:
            stock_data[ column ] = pd.to_numeric( stock_data[ column ], errors = 'coerce' )
        
        # Convert Volume to integer
        stock_data[ "Volume" ] = pd.to_numeric( stock_data[ "Volume" ], errors = 'coerce' ).fillna( 0 ).astype( int )
        
        # Remove any rows with NaN values
        stock_data = stock_data.dropna()
        
        return stock_data
        
    except Exception as e:
        st.error( f"Error downloading data: { e }" )
        return pd.DataFrame()

def main():
    st.set_page_config( page_title = "Stock Analysis Dashboard", layout = "wide" )
    
    # Header
    st.title( "📈 Stock Analysis Dashboard" )
    st.markdown( "---" )
    
    # Input Section - Each on its own line
    ticker = st.text_input( "Enter Stock Ticker:", value = "AAPL" ).upper()
    
    start_date = st.date_input(
        "Start Date",
        value = datetime.now() - timedelta( days = 365 )
    )
    
    end_date = st.date_input(
        "End Date",
        value = datetime.now()
    )
    
    # Add moving average period selector
    ma_period = st.slider(
        "Moving Average Period (Days)",
        min_value = 5,
        max_value = 200,
        value = 30,
        step = 5,
        help = "Select the number of days for the moving average calculation"
    )
    
    chart_type = st.selectbox(
        "Chart Type",
        options = [ "line", "candle" ],
        index = 0
    )
    
    st.markdown( "---" )
    
    if ticker:
        try:
            # Load data
            data = load_data( ticker, start_date, end_date )
            
            if not data.empty:
                # Calculate moving average with user-selected period
                data[ f'MA{ ma_period }' ] = data[ 'Close' ].rolling( window = ma_period ).mean()
                
                # Get latest values for comparison
                latest_close = float( data[ 'Close' ].iloc[ -1 ] )
                latest_ma = float( data[ f'MA{ ma_period }' ].iloc[ -1 ] )
                
                # Calculate how many days price was below MA
                last_n_days = data.tail( ma_period )
                days_below_ma = sum( last_n_days[ 'Close' ] < last_n_days[ f'MA{ ma_period }' ] )
                
                # Create signal message
                if days_below_ma < ma_period/2:  # Less than half the days below MA
                    st.success( "BUY Signal: Price (${:.2f}) is trending above {}-day MA (${:.2f})".format( 
                        latest_close, ma_period, latest_ma 
                    ) )
                else:  # More than half the days below MA
                    st.error( "SELL Signal: Price (${:.2f}) is trending below {}-day MA (${:.2f})".format( 
                        latest_close, ma_period, latest_ma 
                    ) )
                
                # Create the plot
                mc = mpf.make_marketcolors(
                    up = '#00ff00',
                    down = '#ff0000',
                    edge = 'inherit',
                    wick = 'inherit',
                    volume = 'in',
                    ohlc = 'inherit'
                )
                
                s = mpf.make_mpf_style(
                    marketcolors = mc,
                    gridstyle = '--',
                    y_on_right = True,
                    gridcolor = 'gray',
                    facecolor = 'black',
                    figcolor = 'black',
                    gridaxis = 'both'
                )
                
                # Create additional plot for MA
                ma_plot = mpf.make_addplot( 
                    data[ f'MA{ ma_period }' ],
                    color = 'yellow',
                    width = 1,
                    label = f'{ ma_period }-day MA'
                )
                
                # Plot the chart with MA
                fig, ax = mpf.plot(
                    data,
                    type = chart_type,
                    style = s,
                    volume = True,
                    returnfig = True,
                    title = f'\n{ ticker } Stock Price with { ma_period }-day MA',
                    figratio = ( 16, 8 ),
                    figscale = 1.1,
                    panel_ratios = ( 3, 1 ),
                    addplot = ma_plot
                )
                
                # Add legend
                ax[ 0 ].legend( [ f'{ ma_period }-day MA' ] )
                
                st.pyplot( fig )
                
                # Statistics Section
                col1, col2 = st.columns( 2 )
                
                with col1:
                    st.subheader( "Recent Data" )
                    st.dataframe( data.tail().style.format( {
                        'Open': '${:.2f}',
                        'High': '${:.2f}',
                        'Low': '${:.2f}',
                        'Close': '${:.2f}',
                        'Volume': '{:,.0f}'
                    } ) )
                
                with col2:
                    st.subheader( "Summary Statistics" )
                    summary = pd.DataFrame({
                        'Metric': [
                            'Current Price',
                            'Daily Change',
                            'Volume',
                            'Year High',
                            'Year Low'
                        ],
                        'Value': [
                            f"${ data[ 'Close' ].iloc[ -1 ]:.2f}",
                            f"{ ( ( data[ 'Close' ].iloc[ -1 ] - data[ 'Close' ].iloc[ -2 ] ) / data[ 'Close' ].iloc[ -2 ] * 100 ):.2f}%",
                            f"{ int( data[ 'Volume' ].iloc[ -1 ] ):,}",
                            f"${ data[ 'High' ].max():.2f}",
                            f"${ data[ 'Low' ].min():.2f}"
                        ]
                    })
                    st.dataframe( summary, hide_index = True )
                
            else:
                st.warning( "No data available for the selected date range" )
                
        except Exception as e:
            st.error( f"Error: { str( e ) }. Please check if the ticker symbol is correct." )

if __name__ == "__main__":
    main()
