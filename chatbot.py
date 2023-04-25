import random, requests, openai, threading, logging, os, re, datetime, signal

from telegram.ext import Updater, CommandHandler, CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

# handle functions
def error(update, context):
    logging.warning('Update "%s" caused error "%s"', update, context.error)

def start(update, context):
    logging.info('用户点击了/start')
    user_id = update.message.from_user.id
    user_nickname = update.message.from_user.username

    reply_keyboard = [
        [KeyboardButton('/get')],
    ]
    markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)

    message = "Welcome to the movie recommendation chatbot.！\n" \
              "You can use the following commands：\n" \
              "/genres - get a recommendation bases on your profile\n " \
              "after we got your rating for a movie, we will soon rebuild your profile\n" \
              "and you are expected to get different recommendations" \


    context.bot.send_message(chat_id=user_id, text=message, reply_markup=markup)

## movie functions
# function to handle /start command
def genres(update, context):
    user_id = update.message.from_user.id
    user_nickname = update.message.from_user.username

    keyboard = [[InlineKeyboardButton("Get movies from recommender bot",
                                      # callback_data=str({"with": "action", "without": "Comedy|Drama|Horror"})
                                      callback_data="user_" + str(user_id)
                                      ),
                 ],
                ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Get movies from recommender bot for :{}'.format(user_nickname), reply_markup=reply_markup)


# function to handle button click
def button(update, context):
    logging.info('用户点击了genre按钮')
    query = update.callback_query

    user_id = query.data.split("_")[1]

    ### API
    url = "http://51.120.244.80:11451/get/user/{}".format(user_id)
    response = requests.get(url)
    if response.status_code == 200:
        title_lst = eval(response.text)
    ###

    titles_from_model = ["pulp fiction", "once upon a time in hollywood"]

    if len(title_lst) > 1:
        titles_from_model = title_lst

    movies = []
    buttons = []

    for title in titles_from_model:
        response = requests.get(
            f'https://api.themoviedb.org/3/search/movie?api_key=bfa1c4b7acab32a4eb75aa244f15754f&language=en-US&query={title.split("_")[0].split("(")[0]}&page=1&include_adult=false')
        movie = response.json()["results"][0]
        # movies.append(movie)
        button = InlineKeyboardButton(movie['title'], callback_data="movie_" + str(movie['id'])+"_"+str(title.split("_")[1]))
        buttons.append(button)

    ## 使用userId, 从推荐模型拿到一个电影的list. 然后在本地处理将list转换成TMDB标准电影数据格式, 返沪前端让用户选择, 用户点击返回一个movie_id

    # response = requests.get(f'https://api.themoviedb.org/3/search/movie?api_key=bfa1c4b7acab32a4eb75aa244f15754f&language=en-US&query={}&page=1&include_adult=false')
    #
    # movies = response.json()['results']

    # reply_markup = InlineKeyboardMarkup([buttons])
    reply_markup = InlineKeyboardMarkup([[button] for button in buttons])

    query.message.reply_text('Please choose a movie:', reply_markup=reply_markup)

# function to handle movie button click
def movie_button(update, context):
    logging.info('用户点击了电影详情')
    query = update.callback_query
    movie_id = query.data.split("_")[1] # 用户点击电影之后, 返回一个id. 然后我们给出电影的海报等信息.

    database_movie_id = query.data.split("_")[2]
    logging.info("movie_query: ")
    try:
        response = requests.get(f'https://api.themoviedb.org/3/movie/{movie_id}?api_key=bfa1c4b7acab32a4eb75aa244f15754f&append_to_response=credits')

        title = response.json()['title']
        duration = response.json()['runtime']
        director = response.json()['credits']['crew'][0]['name']
        cast = [actor['name'] for actor in response.json()['credits']['cast']]
        poster_url = f"https://image.tmdb.org/t/p/w500{response.json()['poster_path']}"

        message = f"<b>Title:</b> {title}\n<b>Duration:</b> {duration}\n<b>Director:</b> {director}\n<b>Cast:</b> {', '.join(cast[:10])}"

        keyboard = [
                    # [InlineKeyboardButton(director, callback_data=f'director_{director}')],
                    [InlineKeyboardButton("☆", callback_data=f'fav_1_{database_movie_id}'),
                     InlineKeyboardButton("☆", callback_data=f'fav_2_{database_movie_id}'),
                     InlineKeyboardButton("☆", callback_data=f'fav_3_{database_movie_id}'),
                     InlineKeyboardButton("☆", callback_data=f'fav_4_{database_movie_id}'),
                     InlineKeyboardButton("☆", callback_data=f'fav_5_{database_movie_id}'),],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # send message with movie poster
        query.message.reply_photo(photo=poster_url, caption=message, parse_mode="HTML", reply_markup=reply_markup)
        logging.info("movie replied")
    except Exception as e:
        query.message.reply_text("This movie was not supported by TMDB API")


def add_to_fav(update, context):
    logging.info('用户点击了add to favorite')
    # user_id = update.message.from_user.id
    user_id = update.effective_user.id
    # user_nickname = update.message.from_user.username

    query = update.callback_query
    movie_id = query.data.split('_')[2]

    rating = query.data.split('_')[1] # Str类型
    logging.info(movie_id)

    # 此处将userId, movie_id, rating, 映射到数据库
    payload = {
        "UserId": user_id,
        "MovieId": movie_id,
        "Ratings": rating
    }
    try:
        response = requests.post("http://51.120.244.80:11451/rating", json=payload)

        # sql_add_user_fav(update.effective_user.id, movie_id)
        query.message.reply_text("Successfully Rated, your rating will make change to your recommender profile soon! ")
    except:
        query.message.reply_text("Oops! We have trouble communicating with database")


def build(update, msg):
    update.message.reply_text("need minutes to finish, before you get a response, please don't send anything.")
    url = "http://51.120.244.80:11451/refresh"
    response = requests.get(url)
    if response.status_code == 200:
        update.message.reply_text(response.text)
    else:
        update.message.reply_text("failed to build user profile")


def main():
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    updater = Updater(token="5911043706:AAGns12K-TOD54tor_SNsEqirpyACyt3Dys", use_context=True)
    # get dispatcher to register handlers
    dp = updater.dispatcher

    # dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CommandHandler('get', genres))
    dp.add_handler(CommandHandler('build', build))

    dp.add_handler(CallbackQueryHandler(button, pattern=re.compile(r'^user_.*')))
    dp.add_handler(CallbackQueryHandler(add_to_fav, pattern=re.compile(r'^fav_.*')))
    dp.add_handler(CallbackQueryHandler(movie_button, pattern=re.compile(r'^movie_.*')))

    # start the bot
    updater.start_polling()

    # run the bot until Ctrl-C is pressed
    updater.idle()

if __name__ == '__main__':
    main()