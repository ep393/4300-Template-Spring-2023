import math
import numpy as np

from nltk.tokenize import TreebankWordTokenizer
from sklearn.preprocessing import normalize
from sklearn.feature_extraction.text import TfidfVectorizer
from scipy.sparse.linalg import svds

from cosine_sim import *

def movie_svd(movies_df, k_value):
  """
  Apply the SVD procedure to the movie descriptions (in lower case form) after custom tokenization.
  
  Return the normalized u matrix from applying SVD.
  """
  
  movie_tokens = []
  for i in movies_df["about"]:
    movie_tokens.append(i.lower())

  vectorizer = TfidfVectorizer(stop_words = 'english', max_df = 0.9, min_df = 0.01)
  movie_td_matrix = vectorizer.fit_transform(movie_tokens)

  docs_compressed, _, _ = svds(movie_td_matrix, k = k_value)
  docs_compressed_normed = normalize(docs_compressed)

  return docs_compressed_normed

def movie_feature_cosine_sim(query_id, movie_feature_matrix):
  """
  Movie_feature_matrix is the normalized u matrix derived from applying SVD on the movie descriptions,
  which contains key features of the movie descriptions.

  Use feature vectors of movie descriptions in movie_feature_matrix to compute cosine similarity
  between movies and return the movie indices sorted from most similar to least similar.
  """

  movie_sims = movie_feature_matrix.dot(movie_feature_matrix[query_id, :])
  msort = np.argsort(-movie_sims)
  
  top_movie_idx = [i for i in msort[1:]]
  return top_movie_idx

def find_query_id(movie_title, movie_about, movies_df):
  """
  Find the movie with title as movie_title and description of movie_about in movies_df
  and return the row index of that movie in movies_df.
  
  Return 1 if no such movie is found.
  """
  
  row = movies_df.loc[(movies_df['title'] == movie_title) & (movies_df['about'] == movie_about)]
  if len(row.index) > 0:
    return row.index[0]
  else:
     return 1
    
def svd_weighted_index_search(movie_title, query, movies_df, movie_feature_matrix, index, idf, doc_norms): 
  """
  Compute cosine similarity between query movie and songs using movie description
  and information stored in index, idf, and doc_norms.

  Adjust query vector used in computing cosine similarity by adding query vector
  for top 10 similar movies, found using SVD.
  """
  
  tokenizer = TreebankWordTokenizer()
  # find row index of query movie in movies_df
  query_id = find_query_id(movie_title, query, movies_df)

  # query movie about
  query_words = tokenizer.tokenize(query.lower())
  
  # calculate word count in query
  weighted_word_count = {}
  for word in query_words:
    if word in idf:
      if not(word in weighted_word_count):
        weighted_word_count[word] = 0
      weighted_word_count[word] += 1

  # retrieve top 10 similar movies and create a list of descriptions of similar movies
  sim_movies_idx = movie_feature_cosine_sim(query_id, movie_feature_matrix)[:10]
  sim_query = []
  for i in sim_movies_idx:
    sim_query.append(movies_df.iloc[i]['about'].lower())
  
  # adjust tf vector for the query movie by considering words in the similar movies
  for description in sim_query:
    words = tokenizer.tokenize(description)
    for word in words:
      if word in idf:
        if not(word in weighted_word_count):
          weighted_word_count[word] = 0
        # custom weight for similar movie word is 0.1
        weighted_word_count[word] += 0.1

  # compute query norm
  q_norm = 0
  for word in weighted_word_count:
    q_norm += (weighted_word_count[word] * idf[word]) ** 2
  q_norm = math.sqrt(q_norm)

  # compute numerator for all documents
  dot_prods = accumulate_dot_scores(weighted_word_count, index, idf)
  
  # for each document, compute the sim score
  cosine_sim = []
  
  for i, d_norm in enumerate(doc_norms):
    numerator = dot_prods[i] if i in dot_prods else 0 
    score = 0 if d_norm == 0 else numerator / (q_norm * d_norm)
    cosine_sim.append((score, i))
  
  return sorted(cosine_sim, key=lambda x : x[0], reverse=True)