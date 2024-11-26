import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.graph_objects as go

# set the page configuration
st.set_page_config( layout = "wide" )


# find stock data from yfinance
def fetch_stock_data( ticker, start_date, end_date ):
    """Fetch stock data from Yahoo Finance."""
    try:
        stock = yf.Ticker( ticker )
        data = stock.history( start = start_date, end = end_date )
        return data
    except Exception as e:
        st.error( f"Error fetching data for { ticker }: { str( e ) }" )
        return None

# calculated the moving averages with the dates
def calculate_signals( data, short_window, long_window, initial_investment ):
    """Calculate moving average signals with dates."""
    data[ 'short_ma' ] = data[ 'Close' ].rolling( window = short_window ).mean()
    data[ 'long_ma' ] = data[ 'Close' ].rolling( window = long_window ).mean()
    
    #defines neccasary variables
    current_value = initial_investment
    current_position = 0
    entry_price = None  
    signals_with_dates = []
    
    
    # loops through the data
    for i in range( len( data ) ):
        
        if i > 0:
            price = data[ 'Close' ].iloc[ i ]
            short_ma = data[ 'short_ma' ].iloc[ i ]
            long_ma = data[ 'long_ma' ].iloc[ i ]
            

            if short_ma > long_ma and current_position == 0:
                current_position = 1
                entry_price = price  # Record entry price
                signals_with_dates.append({
                    'date': data.index[ i ].strftime( '%Y-%m-%d' ),
                    'signal': 'BUY',
                    'price': price,
                    'position': current_position,
                    'portfolio_value': round( current_value, 2 ),
                    'short_ma': round( short_ma, 2 ),
                    'long_ma': round( long_ma, 2 )
                })
            elif short_ma < long_ma and current_position == 1:

                if entry_price is not None:
                    returns = ( price - entry_price ) / entry_price
                    current_value = current_value * ( 1 + returns )
                
                current_position = 0
                entry_price = None
                signals_with_dates.append({
                    'date': data.index[ i ].strftime( '%Y-%m-%d' ),
                    'signal': 'SELL',
                    'price': price,
                    'position': current_position,
                    'portfolio_value': round( current_value, 2 ),
                    'short_ma': round( short_ma, 2 ),
                    'long_ma': round( long_ma, 2 )
                })
    

    final_price = data[ 'Close' ].iloc[ -1 ]
    if current_position == 1 and entry_price is not None:
        returns = ( final_price - entry_price ) / entry_price
        current_value = current_value * ( 1 + returns )
    
    final_date = data.index[ -1 ].strftime( '%Y-%m-%d' )
    if not signals_with_dates or signals_with_dates[ -1 ][ 'date' ] != final_date:
        signals_with_dates.append({
            'date': final_date,
            'signal': 'HOLD',
            'price': final_price,
            'position': current_position,
            'portfolio_value': round( current_value, 2 ),
            'short_ma': round( data[ 'short_ma' ].iloc[ -1 ], 2 ),
            'long_ma': round( data[ 'long_ma' ].iloc[ -1 ], 2 )
        })

    return {
        'close': final_price,
        'ma': data[ 'long_ma' ].iloc[ -1 ],
        'signal': signals_with_dates[ -1 ][ 'signal' ],
        'history': signals_with_dates,
        'data': data,
        'final_value': current_value  
    }

def calculate_returns( data_dict, signals, initial_investment = 1000 ):
    """Calculate returns based on trading signals."""
    portfolio_results = {}
    
    for ticker, signal_data in signals.items():
        final_value = signal_data[ 'final_value' ]
        profit = final_value - initial_investment
        roi = ( ( final_value - initial_investment ) / initial_investment ) * 100
        
        portfolio_results[ ticker ] = {
            'initial_investment': initial_investment,
            'final_value': final_value,
            'profit': profit,
            'roi': roi
        }
    
    return portfolio_results

def main():
    st.title( "📈 Stock Moving Average Backtester" )
    
    # Single line inputs
    today = datetime.today()
    default_start = today - timedelta( days = 365 )
    start_date = st.date_input( "Start Date", default_start )
    end_date = st.date_input( "End Date", today )
    short_window = st.number_input( "Short MA Window", 5, 100, 20 )
    long_window = st.number_input( "Long MA Window", 20, 200, 50 )
    ticker_input = st.text_input( "Enter Stock Tickers (comma-separated)", "AAPL, MSFT, GOOGL" )
    
    tickers = [ticker.strip() for ticker in ticker_input.split( "," )]
    
    if tickers:
        try:

            data_dict = {}
            signals = {}
            
            initial_investment = st.number_input(
                "Initial Investment ($)",
                min_value = 100,
                max_value = 1000000,
                value = 1000,
                step = 100
            )
            
            for ticker in tickers:
                data = fetch_stock_data( ticker, start_date, end_date )
                if data is not None:
                    data_dict[ ticker ] = data
                    signals[ ticker ] = calculate_signals( data, short_window, long_window, initial_investment )
            
     
            st.markdown( "---" )
            st.subheader( "📋 Signal History" )
            
            
            signal_cols = st.columns( len( tickers ) )
            
            for idx, ticker in enumerate( tickers ):
                with signal_cols[ idx ]:
                    st.write( f"### { ticker }" )
                    signal_history = signals[ ticker ][ 'history' ]
                    
                    if signal_history:
                        df = pd.DataFrame( signal_history )
                        
                        columns = {
                            'date': 'Date',
                            'signal': 'Signal',
                            'price': 'Price',
                            'position': 'Position',
                            'portfolio_value': 'Portfolio Value',
                            'short_ma': 'Short MA',
                            'long_ma': 'Long MA'
                        }
                        
                        df.rename( columns = columns, inplace = True )
                        
                        df[ 'Price' ] = df[ 'Price' ].round( 2 )
                        df[ 'Position' ] = df[ 'Position' ].map( lambda x: 'Holding' if x == 1 else 'Not Holding' )
                        df[ 'Portfolio Value' ] = df[ 'Portfolio Value' ].map( lambda x: f'${ x:,.2f}' )
                        
                        df[ 'Short MA' ] = df[ 'Short MA' ].fillna( '' )
                        df[ 'Long MA' ] = df[ 'Long MA' ].fillna( '' )
                        
                        def color_signal( val ):
                            if val == 'BUY':
                                return 'color: green'
                            elif val == 'SELL':
                                return 'color: red'
                            return ''
                        
                        st.dataframe(
                            df.style.applymap(
                                color_signal,
                                subset = [ 'Signal' ]
                            ),
                            height = 400
                        )
                    else:
                        st.write( "No signal changes in the selected period" )
            
            st.markdown( "---" )
            st.subheader( "📊 Backtesting Results" )
    
            portfolio_results = calculate_returns( data_dict, signals, initial_investment )
            
            cols = st.columns( len( tickers ) )
            for idx, ( ticker, results ) in enumerate( portfolio_results.items() ):
                with cols[ idx ]:
                    st.metric(
                        label = f"{ ticker } Returns",
                        value = f"${ results[ 'final_value' ]:.2f}",
                        delta = f"{ results[ 'roi' ]:.2f}%"
                    )
                    
                    st.write( f"Initial Investment: ${ results[ 'initial_investment' ]:.2f}" )
                    st.write( f"Profit/Loss: ${ results[ 'profit' ]:.2f}" )
            
            total_investment = sum( r[ 'initial_investment' ] for r in portfolio_results.values() )
            total_final = sum( r[ 'final_value' ] for r in portfolio_results.values() )
            total_profit = total_final - total_investment
            total_roi = ( ( total_final - total_investment ) / total_investment ) * 100
            
            st.markdown( "---" )
            st.subheader( "📈 Total Portfolio Performance" )
            col1, col2, col3 = st.columns( 3 )
            
            with col1:
                st.metric(
                    label = "Total Investment",
                    value = f"${ total_investment:.2f}"
                )
            
            with col2:
                st.metric(
                    label = "Total Current Value",
                    value = f"${ total_final:.2f}",
                    delta = f"{ total_roi:.2f}%"
                )
            
            with col3:
                st.metric(
                    label = "Total Profit/Loss",
                    value = f"${ total_profit:.2f}"
                )
            
            st.markdown( "---" )
            st.subheader( "📊 Price Charts" )
            
            for ticker, data in data_dict.items():
                st.write( f"### { ticker }" )
                
                fig = go.Figure()
                
                fig.add_trace(
                    go.Candlestick(
                        x = data.index,
                        open = data[ 'Open' ],
                        high = data[ 'High' ],
                        low = data[ 'Low' ],
                        close = data[ 'Close' ],
                        name = 'Price'
                    )
                )
                
                fig.add_trace(
                    go.Scatter(
                        x = data.index,
                        y = data[ 'Close' ].rolling( window = short_window ).mean(),
                        name = f'{ short_window }d MA',
                        line = dict( color = 'orange' )
                    )
                )
                
                fig.add_trace(
                    go.Scatter(
                        x = data.index,
                        y = data[ 'Close' ].rolling( window = long_window ).mean(),
                        name = f'{ long_window }d MA',
                        line = dict( color = 'blue' )
                    )
                )
                
                fig.update_layout(
                    height = 800,
                    title = f"{ ticker } Price Chart",
                    yaxis_title = "Price",
                    xaxis_title = "Date",
                    template = "plotly_white"
                )
                
                st.plotly_chart( fig, use_container_width = True )
                st.markdown( "---" )  
                    
        except Exception as e:
            st.error( f"An error occurred: { str( e ) }" )
    
    st.markdown( "---" )
    st.markdown(
        """
        <div style='text-align: center; color: #666; padding: 20px;'>
            Made with ❤️ by <a href='https://github.com/Pixelated-Dreamer' style='color: #ff69b4; text-decoration: none;'>pixelcatt</a>
        </div>
        """,
        unsafe_allow_html = True
    )

if __name__ == "__main__":
    main()
