import plotly.graph_objects as go
import radon.complexity as radon_cc

def create_complexity_chart(code):
    """Create a Plotly chart for function complexity distribution."""
    try:
        cc_results = radon_cc.cc_visit(code)
        functions = [
            {"name": block.name, "complexity": block.complexity}
            for block in cc_results
            if block.classname is None
        ]
        
        if not functions:
            return {"error": "No functions found for complexity analysis"}
        
        names = [f["name"] for f in functions]
        complexities = [f["complexity"] for f in functions]
        
        fig = go.Figure(data=[
            go.Bar(
                x=names,
                y=complexities,
                marker_color='#4B8BBE',
                text=complexities,
                textposition='auto'
            )
        ])
        fig.update_layout(
            title="Function Complexity Distribution",
            xaxis_title="Function Name",
            yaxis_title="Cyclomatic Complexity",
            plot_bgcolor='#F5F5F5',
            paper_bgcolor='#F5F5F5',
            font_color='#333333'
        )
        
        return {"chart_html": fig.to_html(full_html=False)}
    
    except Exception as e:
        return {"error": f"Failed to create complexity chart: {str(e)}"}