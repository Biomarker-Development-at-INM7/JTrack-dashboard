import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Output, Input
from dash.exceptions import PreventUpdate

def main_callbacks(app):
    def read_csv_flexible(csv_path):
        """Read comma- or semicolon-delimited CSVs with a small fallback."""
        try:
            df = pd.read_csv(csv_path)
            if len(df.columns) == 1 and ";" in str(df.columns[0]):
                return pd.read_csv(csv_path, sep=";")
            return df
        except Exception:
            return pd.read_csv(csv_path, sep=";")

    def normalize_name(value):
        return str(value).strip().lower().replace("-", "_").replace(" ", "_")

    def detect_simple_data_per_day_dataset(df):
        normalized_columns = {normalize_name(col): col for col in df.columns}
        required = {"subject_id", "study_day", "date", "data_per_day"}
        return required.issubset(set(normalized_columns.keys()))

    def detect_metric_per_day_dataset(df):
        if detect_simple_data_per_day_dataset(df):
            return False

        normalized_columns = {normalize_name(col): col for col in df.columns}
        has_subject = "subject_id" in normalized_columns
        has_time_axis = "study_day" in normalized_columns or "date" in normalized_columns
        if not (has_subject and has_time_axis):
            return False

        excluded = {
            "subject_id",
            "study_day",
            "date",
            "group",
            "diagnosis_code",
            "age",
        }
        metric_columns = [
            col for col in df.select_dtypes(include="number").columns
            if normalize_name(col) not in excluded
        ]
        return len(metric_columns) >= 1

    def get_default_x_y(df):
        if detect_metric_per_day_dataset(df):
            x_value = "Study_day" if "Study_day" in df.columns else next(
                (col for col in df.columns if normalize_name(col) == "study_day"),
                next((col for col in df.columns if normalize_name(col) == "date"), None),
            )
            excluded = {
                "subject_id",
                "study_day",
                "date",
                "group",
                "diagnosis_code",
                "age",
            }
            metric_columns = [
                col for col in df.select_dtypes(include="number").columns.tolist()
                if normalize_name(col) not in excluded
            ]
            y_value = metric_columns[0] if metric_columns else None
            return x_value, y_value

        x_preferred = ["Date", "Study_day", "Timestamp_iso", "Timestamp_ms"]
        y_numeric = df.select_dtypes(include="number").columns.tolist()

        x_value = next((col for col in x_preferred if col in df.columns), None)
        if x_value is None:
            x_value = df.columns[0] if len(df.columns) > 0 else None

        y_value = y_numeric[0] if y_numeric else (df.columns[0] if len(df.columns) > 0 else None)
        return x_value, y_value

    def build_metric_per_day_heatmap(df, subject_column, x_var, y_var):
        if not subject_column or not x_var or not y_var:
            return blank_fig("Per-day file is missing required columns.")

        heatmap_source = df.pivot_table(
            index=subject_column,
            columns=x_var,
            values=y_var,
            aggfunc="mean",
            fill_value=0,
        ).sort_index()

        if heatmap_source.empty:
            return blank_fig("No per-day heatmap data available.")

        fig = go.Figure(
            data=go.Heatmap(
                z=heatmap_source.values,
                x=[str(item) for item in heatmap_source.columns.tolist()],
                y=[str(item) for item in heatmap_source.index.tolist()],
                colorscale="Cividis",
                colorbar={"title": y_var},
            )
        )
        fig.update_layout(
            title=f"{y_var} by {subject_column} and {x_var}",
            margin=dict(l=20, r=20, t=50, b=20),
        )
        return fig

    def build_metric_per_day_mean_trend(df, x_var, y_var):
        if not x_var or not y_var or x_var not in df.columns or y_var not in df.columns:
            return blank_fig("Per-day file is missing required columns.")

        trend_df = df[[x_var, y_var]].copy()
        trend_df[y_var] = pd.to_numeric(trend_df[y_var], errors="coerce")
        trend_df = trend_df.dropna(subset=[y_var])
        if trend_df.empty:
            return blank_fig("No numeric per-day values available.")

        mean_df = trend_df.groupby(x_var, as_index=False)[y_var].mean()
        sem_df = trend_df.groupby(x_var)[y_var].sem().reset_index(name="sem")
        merged_df = mean_df.merge(sem_df, on=x_var, how="left")

        fig = px.line(
            merged_df,
            x=x_var,
            y=y_var,
            markers=True,
            title=f"Mean {y_var} over {x_var}",
            template="simple_white",
        )
        fig.add_traces(
            px.scatter(merged_df, x=x_var, y=y_var, error_y="sem").data
        )
        fig.update_layout(margin=dict(l=20, r=20, t=50, b=20), hovermode="x unified")
        return fig

    @app.callback(
        [Output('x-variable-dropdown', 'options'),
         Output('x-variable-dropdown', 'value'),
         Output('y-variable-dropdown', 'options'),
         Output('y-variable-dropdown', 'value'),
         Output('subject-id', 'options')],
        Input('csv-dropdown', 'value'),
        prevent_initial_call=True
    )
    def update_variable_dropdowns(csv_path):
        print("Main CSV Path received:", csv_path)
        if not csv_path:
            raise PreventUpdate

        df = read_csv_flexible(csv_path)

        # Normalize column name to match Subject_Id even if it's like "subject_id" or "Subject-ID"
        subject_column = next((col for col in df.columns if col.lower().replace('-', '_') == "subject_id"), None)

        subject_options = []
        if subject_column:
            sorted_subject_ids = sorted(map(str, df[subject_column].dropna().unique()))
            subject_options = [{'label': subject, 'value': subject} for subject in sorted_subject_ids]

        variable_options = [{'label': col, 'value': col} for col in df.columns]
        numeric_columns = df.select_dtypes(include='number').columns.tolist()
        y_options = [{'label': col, 'value': col} for col in numeric_columns] or variable_options
        default_x, default_y = get_default_x_y(df)
        return variable_options, default_x, y_options, default_y, subject_options

    
    

    def blank_fig(title_text="Make selections to see a plot"):
        fig = go.Figure(go.Heatmap(z=[[None]], showscale=False, hoverinfo="skip"))
        fig.update_xaxes(visible=False, fixedrange=True)
        fig.update_yaxes(visible=False, fixedrange=True)
        fig.update_layout(title=title_text, margin=dict(l=20, r=20, t=50, b=20))
        return fig

    def _find_subject_col(columns):
        for col in columns:
            if col.lower().replace("-", "_") == "subject_id":
                return col
        return None

    @app.callback(
    [Output("main-plot", "figure"),
     Output("group-plot", "figure")],
    Input("csv-dropdown", "value"),
    Input("x-variable-dropdown", "value"),
    Input("y-variable-dropdown", "value"),
    Input("subject-id", "value")
    )
    def update_plot_dual(csv_path, x_var, y_var, subject_sel):
        if not csv_path:
            raise PreventUpdate

        # --- Load ---
        try:
            df = read_csv_flexible(csv_path)
        except Exception as e:
            err = f"Couldn't read CSV: {e}"
            return blank_fig(err), blank_fig(err)

        subject_column = _find_subject_col(df.columns)
        is_metric_per_day_dataset = detect_metric_per_day_dataset(df)

        # Normalize subject selection to list
        selected_subjects = None
        if subject_sel is not None and subject_column:
            selected_subjects = subject_sel if isinstance(subject_sel, (list, tuple)) else [subject_sel]

        # Prepare copies
        df_all = df.copy()
        if x_var in df_all.columns and df_all[x_var].dtype == "object":
            try:
                df_all[x_var] = pd.to_datetime(df_all[x_var], errors="ignore")
            except Exception:
                pass

        # Apply subject filter for both plots
        filtered_df = df_all
        if selected_subjects and subject_column:
            try:
                filtered_df = df_all[df_all[subject_column].astype(str).isin([str(item) for item in selected_subjects])]
            except Exception:
                pass

        # Clean for plotting (drop NA on required cols when present)
        def _col_ok(c): return c is not None and c in filtered_df.columns
        req_cols = [c for c in [x_var, y_var] if c]
        df_cleaned = filtered_df.dropna(subset=req_cols) if req_cols else filtered_df

        # Consistent subject ordering (for color)
        try:
            sorted_subject_ids = sorted(df_all[subject_column].dropna().astype(str).unique().tolist()) if subject_column else None
        except Exception:
            sorted_subject_ids = None

        if is_metric_per_day_dataset and _col_ok(x_var) and _col_ok(y_var):
            if selected_subjects and subject_column:
                color_column = subject_column
                main_fig = px.line(
                    df_cleaned,
                    x=x_var,
                    y=y_var,
                    color=color_column,
                    markers=True,
                    template="simple_white",
                    title=f"{y_var} over {x_var} for selected subjects",
                    category_orders={subject_column: sorted_subject_ids} if sorted_subject_ids else None,
                )
                main_fig.update_layout(margin=dict(l=20, r=20, t=50, b=20), hovermode="x unified")
            else:
                main_fig = build_metric_per_day_heatmap(df_cleaned, subject_column, x_var, y_var)

            group_fig = build_metric_per_day_mean_trend(df_cleaned, x_var, y_var)
            return main_fig, group_fig

        # ---------------------------
        # Figure A: main-graph (detailed/subject view)
        # ---------------------------
        if not (_col_ok(x_var) and _col_ok(y_var)):
            main_fig = blank_fig("Select valid X and Y to see the raw data plot")
        else:
            color_column = None
            if subject_column and subject_column in df_cleaned.columns:
                color_column = subject_column

            title = f"{y_var} over {x_var}"
            if color_column:
                title += f" by {color_column}"

            common_kwargs = dict(
                data_frame=df_cleaned,
                x=x_var,
                y=y_var,
                color=color_column,
                template="simple_white",
                title=title,
                category_orders={subject_column: sorted_subject_ids} if subject_column and sorted_subject_ids else None,
            )

            main_fig = px.scatter(**common_kwargs)
            main_fig.update_layout(margin=dict(l=20, r=20, t=50, b=20), hovermode="x unified")

        # ---------------------------
        # Figure B: selected-plot (GROUP-BY plot)
        # ---------------------------
        if not _col_ok(y_var):
            group_fig = blank_fig("Pick a valid Y variable for the distribution plot")
        else:
            dist_x = x_var if _col_ok(x_var) else None
            title_suffix = f" by {dist_x}" if dist_x else ""
            group_fig = px.box(
                df_cleaned,
                x=dist_x,
                y=y_var,
                title=f"Box: {y_var}{title_suffix}"
            )
            group_fig.update_layout(margin=dict(l=20, r=20, t=50, b=20))

        return main_fig, group_fig

    # @app.callback(
    #     [Output('selected-plot', 'figure'), Output('mean-plot', 'figure')],
    #     Input('x-variable-dropdown', 'value'),
    #     Input('y-variable-dropdown', 'value'),
    #     Input('subject-id', 'value'),
    #     Input('csv-dropdown', 'value'),
    #     prevent_initial_call=True)
    # def update_plot(x_var, y_var, subject_id,subject_id_end, selected_file):
    #     df_cleaned = pd.DataFrame()
    #     df = pd.read_csv(selected_file)
    #     subject_column = next((col for col in df.columns if col.lower().replace('-', '_') == "subject_id"), None)
    #     # Sort the subject IDs alphabetically
    #     sorted_subject_ids = sorted(df[subject_column].unique())
    #     filtered_df = df[df[subject_column] == subject_id]
    #     if not x_var or not y_var :

    #         df_cleaned = df.dropna(subset=[x_var, y_var])


    #         if  "Data_per_day" in df_cleaned : 
                
    #             # Convert the DataFrame using pivot
    #             df_pivot = df.pivot(index=subject_column, columns='Study_day', values='Data_per_day').reset_index()
    #             #print(df_pivot.columns)
    #             mean_df = df.groupby(x_var, as_index=False)[y_var].mean()
    #             fig2 = px.line(mean_df, x=x_var, y=y_var, title=f'Mean of {y_var}', line_shape='spline')
            
    #             confidence_intervals = df.groupby(x_var)[y_var].agg(['mean', 'sem'])
    #             fig2.add_traces(
    #             px.scatter(confidence_intervals.reset_index(), x=x_var, y='mean', error_y='sem').data
    #             )
    #             if subject_id:
    #                 start_index = df_pivot[subject_column].tolist().index(subject_id)
                
    #                 end_index = df_pivot[subject_column].tolist().index(subject_id_end)
    #                 selected_rows = df_pivot.iloc[start_index:end_index,]
                    
    #                 question_columns = df_pivot.columns[2:22]
    #                 fig = px.imshow(selected_rows[question_columns],  x=question_columns, y=selected_rows[subject_column],
    #                         aspect="auto",color_continuous_scale='blues', title='Heatmap of Data')
                    

    #                 #fig = px.line(data_frame=melted_df, x="Study_day", y="Distance", template="simple_white",color='activity_type', markers=True)
    #                 return fig,fig2
    #             else:

    #                 fig = px.line(df, x=x_var, y=y_var, color=subject_column, markers=True,template="simple_white" ,category_orders={subject_column: sorted_subject_ids})
                    
                        
    #                 return fig, fig2
    #         elif  "Sports" in df_cleaned : 

    #             # Convert the DataFrame using pivot
    #             df_pivot = df_cleaned.pivot(index=subject_column, columns='Study_day', values=y_var).reset_index()
    #             #print(df_pivot.columns)
    #             mean_df = df_cleaned.groupby(x_var, as_index=False)[y_var].mean()
    #             fig2 = px.line(mean_df, x=x_var, y=y_var, title=f'Mean of {y_var}', line_shape='spline')
            
    #             confidence_intervals = df_cleaned.groupby(x_var)[y_var].agg(['mean', 'sem'])
    #             fig2.add_traces(
    #             px.scatter(confidence_intervals.reset_index(), x=x_var, y='mean', error_y='sem').data
    #             )
    #             if subject_id:
    #                 start_index = df_pivot[subject_column].tolist().index(subject_id)
                
    #                 end_index = df_pivot[subject_column].tolist().index(subject_id_end)
    #                 selected_rows = df_pivot.iloc[start_index:end_index,]
    #                 question_columns = df_pivot.columns[2:19]
    #                 fig = px.imshow(selected_rows[question_columns],  x=question_columns, y=selected_rows[subject_column],
    #                         aspect="auto",color_continuous_scale='blues', title='Heatmap of Data')
    #             else:

    #                 fig = px.line(df_cleaned, x=x_var, y=y_var, color=subject_column, markers=True,template="simple_white" ,category_orders={subject_column: sorted_subject_ids})
                    
                        
    #             return fig, fig2
    #         else: 
    #             # Initialize an empty DataFrame for melted data
    #             melted_df = pd.DataFrame(columns=[subject_column, "Study_day","Date", "Activity", "Distance (km)"])

    #             # Melt the DataFrame to transform it
    #             melted_df = pd.melt(filtered_df,id_vars=[subject_column, 'Study_day','Date'], var_name='activity_type', value_name='Distance')

                
    #             mean_df = df_cleaned.groupby(x_var, as_index=False)[y_var].mean()
    #             fig2 = px.line(mean_df, x=x_var, y=y_var, title=f'Mean of {y_var}', line_shape='spline')
            
    #             confidence_intervals = df_cleaned.groupby(x_var)[y_var].agg(['mean', 'sem'])
    #             fig2.add_traces(
    #             px.scatter(confidence_intervals.reset_index(), x=x_var, y='mean', error_y='sem').data
    #             )
    #             if subject_id:
    #                 print(melted_df.columns)
    #                 fig = px.line(data_frame=melted_df, x="Study_day", y="Distance", template="simple_white",color='activity_type', markers=True)
                    

    #                 #fig = px.line(data_frame=melted_df, x="Study_day", y="Distance", template="simple_white",color='activity_type', markers=True)
    #                 return fig,fig2
    #             else:

    #                 fig = px.line(df_cleaned, x=x_var, y=y_var, color=subject_column, markers=True,template="simple_white" ,category_orders={subject_column: sorted_subject_ids})
                    
                        
    #                 return fig, fig2
    #     else:
    #         fig2=""
    #         df_cleaned = df.dropna(subset=[x_var, y_var])
    #         if "Distance_by_Activity" in selected_file:
    #             # Initialize an empty DataFrame for melted data
    #             melted_df = pd.DataFrame(columns=[subject_column, "Study_day","Date", "Activity", "Distance (km)"])

    #             # Melt the DataFrame to transform it
    #             melted_df = pd.melt(filtered_df,id_vars=[subject_column, 'Study_day','Date'], var_name='activity_type', value_name='Distance')

                
    #             mean_df = df_cleaned.groupby(x_var, as_index=False)[y_var].mean()
    #             fig2 = px.line(mean_df, x=x_var, y=y_var, title=f'Mean of {y_var}', line_shape='spline')
            
    #             confidence_intervals = df_cleaned.groupby(x_var)[y_var].agg(['mean', 'sem'])
    #             fig2.add_traces(
    #             px.scatter(confidence_intervals.reset_index(), x=x_var, y='mean', error_y='sem').data
    #             )
    #             if subject_id:
    #                 print(melted_df.columns)
    #                 fig = px.line(data_frame=melted_df, x="Study_day", y="Distance", template="simple_white",color='activity_type', markers=True)
    #             else:

    #                 fig = px.line(df_cleaned, x=x_var, y=y_var, color=subject_column, markers=True,template="simple_white" ,category_orders={subject_column: sorted_subject_ids})
                    
                        
    #             return fig, fig2
    #         else:
    #             if subject_id:
    #                 start_index = df[subject_column].tolist().index(subject_id)
                
    #                 end_index = df[subject_column].tolist().index(subject_id_end)
    #                 selected_rows = df.iloc[start_index:end_index,]
                    
    #                 question_columns = df.columns[2:22]
    #                 # need to show 
    #                 fig = px.imshow(selected_rows[question_columns],  x=question_columns, y=selected_rows[subject_column],
    #                             aspect="auto",color_continuous_scale='Cividis', title='Heatmap of Data')
    #             else:
    #                 fig = px.line(df, x=x_var, y=y_var, color=subject_column, markers=True,template="simple_white" ,category_orders={subject_column: sorted_subject_ids})
    #             numeric_columns = [col for col in df.columns if col.isdigit()]
    #             # Melt the DataFrame to create a long-format version for the histogram
    #             df_melted = pd.melt(df, id_vars=[subject_column],value_vars=numeric_columns, var_name='Question', value_name='Value')

    #             # Create a histogram plot using Plotly Express
    #             fig2 = px.histogram(df_melted, x='Value', title='Histogram of Question Columns')

                
                
                
    #             return fig, fig2
   
            
            
            

