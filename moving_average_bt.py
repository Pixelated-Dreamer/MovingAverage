import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

def load_data( tickers, start_date, end_date ):
    """Load and clean stock data for multiple tickers."""
    try:
        data_dict = {}
        for ticker in tickers:
            # Create a Ticker object
            stock = yf.Ticker( ticker )
            
            # Download historical data
            stock_data = stock.history(
                start = start_date,
                end = end_date,
                interval = "1d"
            )
            
            if not stock_data.empty:
                data_dict[ ticker ] = stock_data
            
        return data_dict
        
    except Exception as e:
        st.error( f"Error downloading data: { e }" )
        return {}

def create_interactive_plot( data_dict, ma_period ):
    """Create interactive plot with OHLC and MA for multiple tickers."""
    
    # Create figure with secondary y-axis
    fig = make_subplots(
        rows = len( data_dict ),
        cols = 1,
        subplot_titles = list( data_dict.keys() ),
        vertical_spacing = 0.05,
        specs = [ [ { "secondary_y": True } ] for _ in range( len( data_dict ) ) ]
    )
    
    row = 1
    signals = {}
    
    for ticker, data in data_dict.items():
        # Calculate MA
        data[ f'MA{ ma_period }' ] = data[ 'Close' ].rolling( window = ma_period ).mean()
        
        # Add candlestick
        fig.add_trace(
            go.Candlestick(
                x = data.index,
                open = data[ 'Open' ],
                high = data[ 'High' ],
                low = data[ 'Low' ],
                close = data[ 'Close' ],
                name = ticker,
                showlegend = False
            ),
            row = row,
            col = 1
        )
        
        # Add MA line
        fig.add_trace(
            go.Scatter(
                x = data.index,
                y = data[ f'MA{ ma_period }' ],
                name = f'{ ma_period }d MA',
                line = dict( color = 'yellow' ),
                showlegend = False
            ),
            row = row,
            col = 1
        )
        
        # Add volume bars
        fig.add_trace(
            go.Bar(
                x = data.index,
                y = data[ 'Volume' ],
                name = 'Volume',
                showlegend = False,
                marker = dict(
                    color = 'rgba(100, 100, 100, 0.3)'
                )
            ),
            row = row,
            col = 1,
            secondary_y = True
        )
        
        # Calculate signal
        last_n_days = data.tail( ma_period )
        days_below_ma = sum( last_n_days[ 'Close' ] < last_n_days[ f'MA{ ma_period }' ] )
        latest_close = float( data[ 'Close' ].iloc[ -1 ] )
        latest_ma = float( data[ f'MA{ ma_period }' ].iloc[ -1 ] )
        
        signals[ ticker ] = {
            'signal': 'BUY' if days_below_ma < ma_period/2 else 'SELL',
            'close': latest_close,
            'ma': latest_ma
        }
        
        row += 1
    
    # Update layout
    fig.update_layout(
        height = 300 * len( data_dict ),
        title_text = "Stock Analysis Dashboard",
        template = "plotly_dark",
        xaxis_rangeslider_visible = False
    )
    
    return fig, signals

def main():
    st.set_page_config( page_title = "Stock Analysis Dashboard", layout = "wide" )
    
    # Header
    st.title( "📈 Stock Analysis Dashboard" )
    st.markdown( "---" )
    
    # Each input on its own line
    ticker_input = st.text_input(
        "Enter Stock Tickers (comma-separated):",
        value = "AAPL, MSFT, GOOGL",
        help = "Example: AAPL, MSFT, GOOGL, NVDA, AMZN"
    ).upper()
    
    # Convert input to list of tickers
    tickers = [ ticker.strip() for ticker in ticker_input.split( ',' ) if ticker.strip() ]
    
    # Date inputs and MA slider each on their own line
    start_date = st.date_input(
        "Start Date",
        value = datetime.now() - timedelta( days = 365 )
    )
    
    end_date = st.date_input(
        "End Date",
        value = datetime.now()
    )
    
    ma_period = st.slider(
        "Moving Average Period (Days)",
        min_value = 5,
        max_value = 200,
        value = 30,
        step = 5,
        help = "Select the number of days for the moving average calculation"
    )
    
    st.markdown( "---" )
    
    if tickers:
        try:
            # Load data
            data_dict = load_data( tickers, start_date, end_date )
            
            if data_dict:
                # Create interactive plot
                fig, signals = create_interactive_plot( data_dict, ma_period )
                
                # Display signals in a grid
                num_cols = min( len( tickers ), 4 )  # Maximum 4 columns
                num_rows = ( len( tickers ) + num_cols - 1 ) // num_cols
                
                for row in range( num_rows ):
                    cols = st.columns( num_cols )
                    for col in range( num_cols ):
                        idx = row * num_cols + col
                        if idx < len( tickers ):
                            ticker = tickers[ idx ]
                            if ticker in signals:
                                signal_data = signals[ ticker ]
                                with cols[ col ]:
                                    if signal_data[ 'signal' ] == 'BUY':
                                        st.success( 
                                            f"{ ticker }\n"
                                            f"Signal: BUY\n"
                                            f"Price: ${ signal_data[ 'close' ]:.2f}\n"
                                            f"MA{ ma_period }: ${ signal_data[ 'ma' ]:.2f}"
                                        )
                                    else:
                                        st.error(
                                            f"{ ticker }\n"
                                            f"Signal: SELL\n"
                                            f"Price: ${ signal_data[ 'close' ]:.2f}\n"
                                            f"MA{ ma_period }: ${ signal_data[ 'ma' ]:.2f}"
                                        )
                
                # Display interactive plot
                st.plotly_chart( fig, use_container_width = True )
                
                # Display statistics in expandable sections
                for ticker, data in data_dict.items():
                    with st.expander( f"{ ticker } Statistics" ):
                        col1, col2 = st.columns( 2 )
                        
                        with col1:
                            st.subheader( "Recent OHLCV Data" )
                            st.dataframe( data.tail().style.format( {
                                'Open': '${:.2f}',
                                'High': '${:.2f}',
                                'Low': '${:.2f}',
                                'Close': '${:.2f}',
                                'Volume': '{:,.0f}'
                            } ) )
                        
                        with col2:
                            st.subheader( "Summary" )
                            summary = pd.DataFrame({
                                'Metric': [
                                    'Current Price',
                                    f'{ ma_period }-day MA',
                                    'Daily Change',
                                    'Volume',
                                    'Year High',
                                    'Year Low'
                                ],
                                'Value': [
                                    f"${ data[ 'Close' ].iloc[ -1 ]:.2f}",
                                    f"${ data[ f'MA{ ma_period }' ].iloc[ -1 ]:.2f}",
                                    f"{ ( ( data[ 'Close' ].iloc[ -1 ] - data[ 'Close' ].iloc[ -2 ] ) / data[ 'Close' ].iloc[ -2 ] * 100 ):.2f}%",
                                    f"{ int( data[ 'Volume' ].iloc[ -1 ] ):,}",
                                    f"${ data[ 'High' ].max():.2f}",
                                    f"${ data[ 'Low' ].min():.2f}"
                                ]
                            })
                            st.dataframe( summary, hide_index = True )
            else:
                st.warning( "No data available for the selected tickers and date range" )
                
        except Exception as e:
            st.error( f"Error: { str( e ) }. Please check if the ticker symbols are correct." )

if __name__ == "__main__":
    main()
