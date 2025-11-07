import os, base64, io,json
import pandas as pd
import plotly.express as px
from dash import Output, Input
from dash.exceptions import PreventUpdate

def register_main_callbacks(app):
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
        [Output('selected-plot', 'figure'), Output('mean-plot', 'figure')],
        Input('x-variable-dropdown', 'value'),
        Input('y-variable-dropdown', 'value'),
        Input('subject-id', 'value'),
        Input('subject-id-end', 'value'),
        Input('csv-dropdown', 'value'),
        prevent_initial_call=True)
    def update_plot(x_var, y_var, subject_id,subject_id_end, selected_file):
        df_cleaned = pd.DataFrame()
        df = pd.read_csv(selected_file)
        subject_column = next((col for col in df.columns if col.lower().replace('-', '_') == "subject_id"), None)
        # Sort the subject IDs alphabetically
        sorted_subject_ids = sorted(df[subject_column].unique())
        filtered_df = df[df[subject_column] == subject_id]
        if not x_var or not y_var :

            df_cleaned = df.dropna(subset=[x_var, y_var])


            if  "Data_per_day" in df_cleaned : 
                
                # Convert the DataFrame using pivot
                df_pivot = df.pivot(index=subject_column, columns='Study_day', values='Data_per_day').reset_index()
                #print(df_pivot.columns)
                mean_df = df.groupby(x_var, as_index=False)[y_var].mean()
                fig2 = px.line(mean_df, x=x_var, y=y_var, title=f'Mean of {y_var}', line_shape='spline')
            
                confidence_intervals = df.groupby(x_var)[y_var].agg(['mean', 'sem'])
                fig2.add_traces(
                px.scatter(confidence_intervals.reset_index(), x=x_var, y='mean', error_y='sem').data
                )
                if subject_id:
                    start_index = df_pivot[subject_column].tolist().index(subject_id)
                
                    end_index = df_pivot[subject_column].tolist().index(subject_id_end)
                    selected_rows = df_pivot.iloc[start_index:end_index,]
                    
                    question_columns = df_pivot.columns[2:22]
                    fig = px.imshow(selected_rows[question_columns],  x=question_columns, y=selected_rows[subject_column],
                            aspect="auto",color_continuous_scale='blues', title='Heatmap of Data')
                    

                    #fig = px.line(data_frame=melted_df, x="Study_day", y="Distance", template="simple_white",color='activity_type', markers=True)
                    return fig,fig2
                else:

                    fig = px.line(df, x=x_var, y=y_var, color=subject_column, markers=True,template="simple_white" ,category_orders={subject_column: sorted_subject_ids})
                    
                        
                    return fig, fig2
            elif  "Sports" in df_cleaned : 

                # Convert the DataFrame using pivot
                df_pivot = df_cleaned.pivot(index=subject_column, columns='Study_day', values=y_var).reset_index()
                #print(df_pivot.columns)
                mean_df = df_cleaned.groupby(x_var, as_index=False)[y_var].mean()
                fig2 = px.line(mean_df, x=x_var, y=y_var, title=f'Mean of {y_var}', line_shape='spline')
            
                confidence_intervals = df_cleaned.groupby(x_var)[y_var].agg(['mean', 'sem'])
                fig2.add_traces(
                px.scatter(confidence_intervals.reset_index(), x=x_var, y='mean', error_y='sem').data
                )
                if subject_id:
                    start_index = df_pivot[subject_column].tolist().index(subject_id)
                
                    end_index = df_pivot[subject_column].tolist().index(subject_id_end)
                    selected_rows = df_pivot.iloc[start_index:end_index,]
                    question_columns = df_pivot.columns[2:19]
                    fig = px.imshow(selected_rows[question_columns],  x=question_columns, y=selected_rows[subject_column],
                            aspect="auto",color_continuous_scale='blues', title='Heatmap of Data')
                else:

                    fig = px.line(df_cleaned, x=x_var, y=y_var, color=subject_column, markers=True,template="simple_white" ,category_orders={subject_column: sorted_subject_ids})
                    
                        
                return fig, fig2
            else: 
                # Initialize an empty DataFrame for melted data
                melted_df = pd.DataFrame(columns=[subject_column, "Study_day","Date", "Activity", "Distance (km)"])

                # Melt the DataFrame to transform it
                melted_df = pd.melt(filtered_df,id_vars=[subject_column, 'Study_day','Date'], var_name='activity_type', value_name='Distance')

                
                mean_df = df_cleaned.groupby(x_var, as_index=False)[y_var].mean()
                fig2 = px.line(mean_df, x=x_var, y=y_var, title=f'Mean of {y_var}', line_shape='spline')
            
                confidence_intervals = df_cleaned.groupby(x_var)[y_var].agg(['mean', 'sem'])
                fig2.add_traces(
                px.scatter(confidence_intervals.reset_index(), x=x_var, y='mean', error_y='sem').data
                )
                if subject_id:
                    print(melted_df.columns)
                    fig = px.line(data_frame=melted_df, x="Study_day", y="Distance", template="simple_white",color='activity_type', markers=True)
                    

                    #fig = px.line(data_frame=melted_df, x="Study_day", y="Distance", template="simple_white",color='activity_type', markers=True)
                    return fig,fig2
                else:

                    fig = px.line(df_cleaned, x=x_var, y=y_var, color=subject_column, markers=True,template="simple_white" ,category_orders={subject_column: sorted_subject_ids})
                    
                        
                    return fig, fig2
        else:
            fig2=""
            df_cleaned = df.dropna(subset=[x_var, y_var])
            if "Distance_by_Activity" in selected_file:
                # Initialize an empty DataFrame for melted data
                melted_df = pd.DataFrame(columns=[subject_column, "Study_day","Date", "Activity", "Distance (km)"])

                # Melt the DataFrame to transform it
                melted_df = pd.melt(filtered_df,id_vars=[subject_column, 'Study_day','Date'], var_name='activity_type', value_name='Distance')

                
                mean_df = df_cleaned.groupby(x_var, as_index=False)[y_var].mean()
                fig2 = px.line(mean_df, x=x_var, y=y_var, title=f'Mean of {y_var}', line_shape='spline')
            
                confidence_intervals = df_cleaned.groupby(x_var)[y_var].agg(['mean', 'sem'])
                fig2.add_traces(
                px.scatter(confidence_intervals.reset_index(), x=x_var, y='mean', error_y='sem').data
                )
                if subject_id:
                    print(melted_df.columns)
                    fig = px.line(data_frame=melted_df, x="Study_day", y="Distance", template="simple_white",color='activity_type', markers=True)
                else:

                    fig = px.line(df_cleaned, x=x_var, y=y_var, color=subject_column, markers=True,template="simple_white" ,category_orders={subject_column: sorted_subject_ids})
                    
                        
                return fig, fig2
            else:
                print(df)
                if subject_id:
                    start_index = df[subject_column].tolist().index(subject_id)
                
                    end_index = df[subject_column].tolist().index(subject_id_end)
                    selected_rows = df.iloc[start_index:end_index,]
                    
                    question_columns = df.columns[2:22]
                    # need to show 
                    fig = px.imshow(selected_rows[question_columns],  x=question_columns, y=selected_rows[subject_column],
                                aspect="auto",color_continuous_scale='Cividis', title='Heatmap of Data')
                else:
                    fig = px.line(df, x=x_var, y=y_var, color=subject_column, markers=True,template="simple_white" ,category_orders={subject_column: sorted_subject_ids})
                numeric_columns = [col for col in df.columns if col.isdigit()]
                # Melt the DataFrame to create a long-format version for the histogram
                df_melted = pd.melt(df, id_vars=[subject_column],value_vars=numeric_columns, var_name='Question', value_name='Value')

                # Create a histogram plot using Plotly Express
                fig2 = px.histogram(df_melted, x='Value', title='Histogram of Question Columns')

                
                
                
                return fig, fig2
   
            
            
            