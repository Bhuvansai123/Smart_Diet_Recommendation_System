import numpy as np
import re
import pandas as pd
import streamlit as st
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import NearestNeighbors
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer
import os


# Load dataset once at module level
@st.cache_data
def load_dataset():
    # Try multiple paths for different deployment scenarios
    possible_paths = [
        os.path.join(os.path.dirname(__file__), '..', 'Data', 'dataset_enhanced.csv'),  # Local with cuisine tags
        os.path.join(os.path.dirname(__file__), '..', 'Data', 'dataset.csv'),  # Fallback to original
        os.path.join('Data', 'dataset_enhanced.csv'),  # Streamlit Cloud
        os.path.join('Data', 'dataset.csv'),  # Alternative
        'Data/dataset_enhanced.csv',
        'Data/dataset.csv'
    ]
    
    for dataset_path in possible_paths:
        if os.path.exists(dataset_path):
            df = pd.read_csv(dataset_path, compression='gzip')
            # Check if Cuisine column exists, if not add it as 'Other'
            if 'Cuisine' not in df.columns:
                df['Cuisine'] = 'Other'
            return df
    
    # If none found, raise error
    raise FileNotFoundError("Could not find dataset.csv or dataset_enhanced.csv in expected locations")


def scaling(dataframe):
    scaler = StandardScaler()
    prep_data = scaler.fit_transform(dataframe.iloc[:, 6:15].to_numpy())
    return prep_data, scaler


def nn_predictor(prep_data):
    neigh = NearestNeighbors(metric='cosine', algorithm='brute')
    neigh.fit(prep_data)
    return neigh


def build_pipeline(neigh, scaler, params):
    transformer = FunctionTransformer(neigh.kneighbors, kw_args=params)
    pipeline = Pipeline([('std_scaler', scaler), ('NN', transformer)])
    return pipeline


def extract_data(dataframe, ingredients):
    extracted_data = dataframe.copy()
    extracted_data = extract_ingredient_filtered_data(extracted_data, ingredients)
    return extracted_data


def extract_ingredient_filtered_data(dataframe, ingredients):
    extracted_data = dataframe.copy()
    regex_string = ''.join(map(lambda x: f'(?=.*{x})', ingredients))
    extracted_data = extracted_data[extracted_data['RecipeIngredientParts'].str.contains(
        regex_string, regex=True, flags=re.IGNORECASE)]
    return extracted_data


def apply_pipeline(pipeline, _input, extracted_data):
    _input = np.array(_input).reshape(1, -1)
    return extracted_data.iloc[pipeline.transform(_input)[0]]


def recommend(dataframe, _input, ingredients=[], params={'n_neighbors': 5, 'return_distance': False}):
    extracted_data = extract_data(dataframe, ingredients)
    if extracted_data.shape[0] >= params['n_neighbors']:
        prep_data, scaler = scaling(extracted_data)
        neigh = nn_predictor(prep_data)
        pipeline = build_pipeline(neigh, scaler, params)
        return apply_pipeline(pipeline, _input, extracted_data)
    else:
        return None


def extract_quoted_strings(s):
    strings = re.findall(r'"([^"]*)"', s)
    return strings


def output_recommended_recipes(dataframe):
    if dataframe is not None:
        output = dataframe.copy()
        output = output.to_dict("records")
        for recipe in output:
            recipe['RecipeIngredientParts'] = extract_quoted_strings(recipe['RecipeIngredientParts'])
            recipe['RecipeInstructions'] = extract_quoted_strings(recipe['RecipeInstructions'])
    else:
        output = None
    return output


class Generator:
    def __init__(self, nutrition_input: list, ingredients: list = [], params: dict = {'n_neighbors': 5, 'return_distance': False}):
        self.nutrition_input = nutrition_input
        self.ingredients = ingredients
        self.params = params
        self.dataset = load_dataset()

    def set_request(self, nutrition_input: list, ingredients: list, params: dict):
        self.nutrition_input = nutrition_input
        self.ingredients = ingredients
        self.params = params

    def generate(self):
        # Use local model instead of API call
        recommended = recommend(
            self.dataset,
            self.nutrition_input,
            self.ingredients,
            self.params
        )
        output = output_recommended_recipes(recommended)
        
        # Return in same format as API response
        class Response:
            def __init__(self):
                self.status_code = 200
                
            def json(self):
                return {'output': output}
        
        return Response()
