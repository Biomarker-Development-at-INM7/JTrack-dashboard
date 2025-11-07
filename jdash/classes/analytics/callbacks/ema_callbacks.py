import os, base64, io,json
import pandas as pd
import plotly.express as px
from dash import Output, Input
from dash.exceptions import PreventUpdate

def register_ema_callbacks(app):
    @app.callback(
        [Output('x-variable-dropdown', 'options'),
         Output('y-variable-dropdown', 'options'),
         Output('subject-id', 'options'),
         Output('subject-id-end', 'options')],
        Input('csv-dropdown', 'value'),
        prevent_initial_call=True
    )
    def update_variable_dropdowns(csv_path):
        print("CSV Path received:", csv_path)
        if not csv_path:
            raise PreventUpdate

        df = pd.read_csv(csv_path)

        # Normalize column name to match Subject_Id even if it's like "subject_id" or "Subject-ID"
        subject_column = next((col for col in df.columns if col.lower().replace('-', '_') == "subject_id"), None)
        if not subject_column:
            raise PreventUpdate  # or return empty options

        sorted_subject_ids = sorted(df[subject_column].unique())
        variable_options = [{'label': col, 'value': col} for col in df.columns]

        return variable_options[1:], variable_options[1:], sorted_subject_ids, sorted_subject_ids

    @app.callback(
        [Output('selected-plot', 'figure'),
        Output('mean-plot', 'figure')],
        Input('x-variable-dropdown', 'value'),
        Input('y-variable-dropdown', 'value'),
        Input('subject-id', 'value'),
        Input('subject-id-end', 'value'),
        Input('csv-dropdown', 'value'),
        prevent_initial_call=True)
    def update_plot(x_var, y_var, subject_id,subject_id_end, selected_file):
        df = pd.read_csv(selected_file)
        subject_column = next((col for col in df.columns if col.lower().replace('-', '_') == "subject_id"), None)
        # Sort the subject IDs alphabetically
        sorted_subject_ids = sorted(df[subject_column].unique())
        if  x_var or  y_var :            
            filtered_df = df[df[subject_column] == subject_id]
            df_cleaned = df.dropna(subset=[x_var, y_var])
            fig = px.line(df, x=x_var, y=y_var, color=subject_column, 
                          markers=True,template="simple_white" ,
                          category_orders={subject_column: sorted_subject_ids})
            
            return fig, px.bar()
        elif subject_id or subject_id_end:
            fig2=""
            
            if subject_id:
                start_index = df[subject_column].tolist().index(subject_id)
                
                end_index = df[subject_column].tolist().index(subject_id_end)
                selected_rows = df.iloc[start_index:end_index,]

                question_columns = df.columns[2:22]
                # need to show 
                fig = px.imshow(selected_rows[question_columns],
                                x=question_columns, y=selected_rows[subject_column],
                                aspect="auto",color_continuous_scale='Cividis', 
                                title='Heatmap of Data')
            
                
            #print(df_pivot.columns)

            # Select only the 'Question' columns for the histogram
            question_columns = df.columns[df.columns.str.startswith('Question_')]

            # Melt the DataFrame to create a long-format version for the histogram
            df_melted = pd.melt(df, id_vars=[subject_column], 
                                value_vars=question_columns, 
                                var_name='Question', value_name='Value')

            # Create a histogram plot using Plotly Express
            fig2 = px.histogram(df_melted, x='Value', 
                                color='Question', 
                                title='Histogram of Question Columns')

            #fig2 = px.histogram(
            #        df_cleaned,
            #        x=y_var,
            #        nbins=20,  # Number of bins or bars in the histogram
            #        title='Histogram of Data',
            #        labels={'Values': 'Value', 'count': 'Frequency'}
            #    )
            
            
            return fig, fig2
        else:
            raise PreventUpdate
        