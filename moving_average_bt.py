import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

st.set_page_config( layout = "wide" ) 

def fetch_stock_data( ticker, start_date, end_date ):
    """Fetch stock data from Yahoo Finance."""
    try:
        stock = yf.Ticker( ticker )
        data = stock.history( start = start_date, end = end_date )
        return data
    except Exception as e:
        st.error( f"Error fetching data for { ticker }: { str( e ) }" )
        return None

def calculate_signals( data, short_window, long_window ):
    """Calculate moving average signals with dates."""
    data[ 'short_ma' ] = data[ 'Close' ].rolling( window = short_window ).mean()
    data[ 'long_ma' ] = data[ 'Close' ].rolling( window = long_window ).mean()
    
    # Generate signals
    data[ 'signal' ] = np.where( data[ 'short_ma' ] > data[ 'long_ma' ], 'BUY', 'SELL' )
    
    # Detect signal changes
    data[ 'signal_change' ] = data[ 'signal' ] != data[ 'signal' ].shift( 1 )
    signal_dates = data[data[ 'signal_change' ]].index
    
    signals_with_dates = []
    for date in signal_dates:
        signals_with_dates.append({
            'date': date.strftime( '%Y-%m-%d' ),
            'signal': data.loc[date, 'signal'],
            'price': data.loc[date, 'Close']
        })
    
    return {
        'close': data[ 'Close' ].iloc[ -1 ],
        'ma': data[ 'long_ma' ].iloc[ -1 ],
        'signal': data[ 'signal' ].iloc[ -1 ],
        'history': signals_with_dates
    }

def calculate_returns( data_dict, signals, initial_investment = 1000 ):
    """Calculate returns based on trading signals."""
    portfolio_results = {}
    
    for ticker, data in data_dict.items():
        signal_data = signals[ ticker ]
        
        # Calculate percentage change from MA crossover
        price_change = ( signal_data[ 'close' ] - signal_data[ 'ma' ] ) / signal_data[ 'ma' ]
        
        # Calculate returns based on signal
        if signal_data[ 'signal' ] == 'BUY':
            returns = initial_investment * ( 1 + price_change )
        else:  # SELL signal
            returns = initial_investment * ( 1 - price_change )
            
        profit = returns - initial_investment
        roi = ( ( returns - initial_investment ) / initial_investment ) * 100
        
        portfolio_results[ ticker ] = {
            'initial_investment': initial_investment,
            'final_value': returns,
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
            # Fetch data for all tickers
            data_dict = {}
            signals = {}
            
            for ticker in tickers:
                data = fetch_stock_data( ticker, start_date, end_date )
                if data is not None:
                    data_dict[ ticker ] = data
                    signals[ ticker ] = calculate_signals( data, short_window, long_window )
            
            # Signal History Tables in a row
            st.markdown( "---" )
            st.subheader( "📋 Signal History" )
            
            # Create columns for each ticker's signal table
            signal_cols = st.columns( len( tickers ) )
            
            for idx, ticker in enumerate( tickers ):
                with signal_cols[ idx ]:
                    st.write( f"### { ticker }" )
                    signal_history = signals[ ticker ][ 'history' ]
                    
                    if signal_history:
                        df = pd.DataFrame( signal_history )
                        df.columns = [ 'Date', 'Signal', 'Price' ]
                        df[ 'Price' ] = df[ 'Price' ].round( 2 )
                        
                        def color_signal( val ):
                            color = 'green' if val == 'BUY' else 'red'
                            return f'color: { color }'
                        
                        st.dataframe(
                            df.style.applymap(
                                color_signal,
                                subset = [ 'Signal' ]
                            )
                        )
                    else:
                        st.write( "No signal changes in the selected period" )
            
            # Backtesting section
            st.markdown( "---" )
            st.subheader( "📊 Backtesting Results" )
    
            initial_investment = st.number_input(
                "Initial Investment ($)",
                min_value = 100,
                max_value = 1000000,
                value = 1000,
                step = 100
            )
            
            portfolio_results = calculate_returns( data_dict, signals, initial_investment )
            
            # Display results in a grid
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
            
            # Calculate total portfolio metrics
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
            
            # Display charts stacked
            st.markdown( "---" )
            st.subheader( "📊 Price Charts" )
            
            for ticker, data in data_dict.items():
                st.write( f"### { ticker }" )
                chart_data = pd.DataFrame({
                    'Price': data[ 'Close' ],
                    f'{ short_window }d MA': data[ 'Close' ].rolling( window = short_window ).mean(),
                    f'{ long_window }d MA': data[ 'Close' ].rolling( window = long_window ).mean()
                })
                st.line_chart( chart_data )
                st.markdown( "---" )  # Add separator between charts
                    
        except Exception as e:
            st.error( f"An error occurred: { str( e ) }" )

if __name__ == "__main__":
    main()

