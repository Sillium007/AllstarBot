import discord
from discord.ext import commands
import json
import sqlite3
import random
import datetime
import locale
import sheets
import os
import setup
import strawpoll
import asyncio

with open('config.json') as json_data_file:
    data = json.load(json_data_file)

if not os.path.exists('db/tabletop.db') or not os.path.exists('db/gta.db') or not os.path.exists('db/quotes.db') or not os.path.exists('db/gifs.db'):
    print("Databases do not exist. Running setup!")
    setup.setup()

def token():
    '''Returns your token wherever it is'''
    if data.get('token') == "<token>":
        if not os.environ.get('TOKEN'):
            print("Error retrieving token.")
            exit()
    else:
        token = data.get('token').strip('\"')
    return os.environ.get('TOKEN') or token
        
bot = commands.Bot(command_prefix=data["command_prefix"], description=data["description"])
# maybe usefull later:
#bot.remove_command("help")

ttsConn = sqlite3.connect('db/tabletop.db')
quotesConn = sqlite3.connect('db/quotes.db')
gifsConn = sqlite3.connect('db/gifs.db')
gtaConn = sqlite3.connect('db/gta.db')

ttsCur = ttsConn.cursor()
quotesCur = quotesConn.cursor()
gifsCur = gifsConn.cursor()
gtaCur = gtaConn.cursor()

try:
    locale.setlocale(locale.LC_ALL, 'German_Germany')
except:
    print("Couldn't set locale")
  
@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')

#@bot.command
#async def help(category : str = ""):
#    helptext = "```"
#    category = category.lower()
#    if category == "":
#        helptext += "Bitte eine Kategorie angeben\n"
#        helptext += "!help <Kategorie>"
#        helptext += "Kategorien:"
#        helptext += "   tts"
#        helptext += "   gta"
#        helptext += "   general"
#    elif category == "tts":
#        helptext += "
#    elif category == "gta":
#    elif category == "general":
#    else:
#        
#    helptext += "```"
    
@bot.command(aliases=["ttssiegeimmonat", "tabletopwinsinmonth", "tabletopsiegeimmonat"])
async def ttswinsinmonth(month : int = None, player : str = ""):
    """Tabletop Siege eines Monats"""
    #Returns all players who won a game in a certain month and the amount of wins
    #If player is given, return the wins in that month of that player
    if month == None:
        await bot.say('```!ttswinsinmonth <month> [game]```')
    else:
        s = '```ml\n'
        if player != "":
            s += "Gewinne fuer Spieler '" + player + "'"
        else:
            s += 'Gewinne pro Spieler'
        s += " im Monat '%s'\n" % datetime.date(1900,month, 1).strftime('%B')
        s += '| {:20s}| {:10s}|\n'.format('Name', 'Wins')
        s += ('-' * 35)
        s += '\n'
        for row in ttsCur.execute("""Select player.name, count(player.name)
                                    from played
                                    join player on playerId = player.rowid
                                    join game on gameId = game.rowid
                                    where strftime('%m', date(playdate)) = '""" + str(month).zfill(2) + """'
                                        AND player.name like '%""" + player + """%'
                                        AND rank = 1
                                    group by player.name"""):
            s += '| {:20s}| {:10s}|\n'.format(str(row[0]), str(row[1]))
        s += '```'
        await bot.say(s)

@bot.command(aliases = ["ttsspielervonspiel", "tabletopplayersofgame"])
async def ttsplayersofgame(game : str = None):
    """Spieler die ein bestimmtes Tabletop Spiel bereits gespielt haben"""
    #Returns all players who played a certain game
    if game == None:
        await bot.say('```!ttsplayersofgame <game>```')
    else:
        s = "```Spieler des Spieles " + game + ":\n"
        first = True
        # TODO: check which games exist for that pattern, like in winpercent function
        for row in ttsCur.execute("""Select player.name
                                    from played
                                    join player on played.playerid = player.rowid
                                    join game on played.gameid = game.rowid
                                    where LOWER(game.name) like '%""" + game.lower() + """%'
                                    group by player.name"""):
            if first == False:
                s += ", "
            else:
                first = False
            s += row[0]
        s += "```"
        await bot.say(s)

@bot.command(aliases = ["ttssiegprozent", "tabletopwinpercent", "tabletopsiegprozent"])
async def ttswinpercent(player : str = None, game : str = ""):
    """Siegesrate eines Spielers"""
    #Returns the winpercent of a player. If game is given, it returns the winpercent for that game
    #TODO: Maybe have "all" as playername for winpercent of all players?
    if player == None:
        await bot.say('```!ttswinpercent <player> [game]```')
    else:
        s = "```Winpercent for player " + player + ""
        gameName = ""
        if game != "":
            try:
                # check if the game exists
                # if multiple games have been found, print an error with information
                errMsg = "```Es wurden mehrere Spiele fuer den Namen '" + game + "' gefunden:\n"
                error = False
                for row in ttsCur.execute("""Select game.name
                                    from game
                                    where LOWER(game.name) like '%""" + game.lower() + """%'
                                    group by game.name"""):
                      
                    if error == True:
                        errMsg += "'" + row[0] + "', "
                    else:
                        if gameName != "":
                            error = True
                            errMsg += "'" + gameName + "', "
                            errMsg += "'" + row[0] + "', "
                        else:
                            gameName = row[0]
                if error == True:
                    errMsg += "```"
                    await bot.say(errMsg)
                    return
                s += " im Spiel " + gameName
            except:
                # Something went wrong, maybe print a better error
                await bot.say("Something went wrong :(")
                return
                     
        s += ":\n"
        try:
            # get number of wins
            ttsCur.execute("""Select count(player.name)
                                from played
                                join player on played.playerid = player.rowid
                                join game on played.gameid = game.rowid
                                where LOWER(player.name) like '%""" + player.lower() + """%'
                                    AND LOWER(game.name) like '%""" + gameName + """%'
                                    AND played.rank = 1
                                    AND played.iscoop = 'False'
                                group by player.name""")

            wins = int(ttsCur.fetchone()[0])
        except:
            wins = 0
            
        try:
            # get number of games played
            ttsCur.execute("""Select count(*)
                                    from played
                                    join player on played.playerid = player.rowid
                                    join game on played.gameid = game.rowid
                                    where LOWER(player.name) like '%""" + player.lower() + """%'
                                        AND LOWER(game.name) like '%""" + gameName + """%'
                                        AND played.iscoop = 'False'""")
            games = int(ttsCur.fetchone()[0])
            winpercent = 100/games*wins
            s += str(round(winpercent,2)) + "% (" + str(games) + " Spiele, " + str(wins) + " Siege)"
            s += "```"
            await bot.say(s)
        except:
            await bot.say("Keine Eintraege fuer Spieler " + player + " gefunden :persevere:")


@bot.command(aliases=["ttssiege", "ttsgewinne", "tabletopwins", "tabletopsiege", "tabletopgewinne"])
async def ttswins(player : str = None, game : str = ""):
    """Tabletop Siege eines Spielers"""
    #Returns how many wins a player has
    #If game is given, returns the wins for that game
    if player == None:
        await bot.say('```!ttswins <player> [game]```')
    else:
        gameName = ""
        if game != "":
            try:
                # check if the game exists
                # if multiple games have been found, print an error with information
                # TODO: put this into a seperate function, is needed multiple times
                errMsg = "```Es wurden mehrere Spiele fuer den Namen '" + game + "' gefunden:\n"
                error = False
                for row in ttsCur.execute("""Select game.name
                                    from game
                                    where LOWER(game.name) like '%""" + game.lower() + """%'
                                    group by game.name"""):
                      
                    if error == True:
                        errMsg += "'" + row[0] + "', "
                    else:
                        if gameName != "":
                            error = True
                            errMsg += "'" + gameName + "', "
                            errMsg += "'" + row[0] + "', "
                        else:
                            gameName = row[0]
                if error == True:
                    errMsg += "```"
                    await bot.say(errMsg)
                    return
            except Exception as e:
                # Something went wrong, maybe print a better error
                print(e)
                await bot.say("Something went wrong :(")
                return
                     
        try:
            # get number of wins
            ttsCur.execute("""Select count(player.name)
                                from played
                                join player on played.playerid = player.rowid
                                join game on played.gameid = game.rowid
                                where LOWER(player.name) like '%""" + player.lower() + """%'
                                    AND LOWER(game.name) like '%""" + gameName + """%'
                                    AND played.rank = 1
                                    AND played.iscoop = 'False'
                                group by player.name""")

            wins = int(ttsCur.fetchone()[0])
        except:
            wins = 0
            
        s = "```Spieler '" + player + "' hat " + str(wins) + " Siege"
        if gameName != "":
            s += " im Spiel '" + gameName + "'"
        s += "```"
        await bot.say(s)


#@bot.command()
#async def phil():
#    await bot.say('Der schoenste Oesterreicher :flag_at:')

@bot.command(aliases=["zitat"])
async def quote(name : str = ""):
    """Zitat eines Communitymitglieds"""
    #Selects a random quote from the database.
    #If a name parameter is given it searches for a quote from that person
    quotesCur.execute("""SELECT quote, name from quotes 
                            WHERE ROWID IN
                                (Select ROWID from quotes
                                    where LOWER(name) like '%"""+name.lower()+"""%' 
                                    ORDER BY RANDOM() LIMIT 1)""")
    row = quotesCur.fetchone()
    if(row != None):
        await bot.say('```\"%s\" - %s```' % (row[0], row[1]))
    else:
        await bot.say("Kein Zitat von '%s' gefunden.\nHier nimm ein :ice_cream: stattdessen." % name)

@bot.command(pass_context=True, aliases=["addzitat"])
async def addquote(ctx, quote : str = None, name : str = None):
    """Neues Zitat erstellen"""
    # Adds one quote to the database. Adds the person who issued the command to the table
    if quote == None or name == None:
        await bot.say('```!addquote "<quote>" "<name>"```')
    else:
        quotesCur.execute("""INSERT INTO quotes (quote, name, addedBy) VALUES ('%s', '%s', '%s')""" % (quote, name, ctx.message.author))
        quotesConn.commit()
        await bot.say("Zitat hinzugefuegt")

#@bot.command(pass_context=True)
#async def test(ctx):
#    """ Testing some permission stuff """
#    await bot.say("author: " + str(ctx.message.author))
#    #for role in ctx.message.author.roles:
#    #    await bot.say("rolle: " + str(role.name))
#    await bot.say("ist admin: " + str(ctx.message.author.server_permissions.administrator))

    
@bot.command()
async def gtaracewins(player : str = None):
    """Anzahl der Siege eines Spielers"""
    #Returns the number of race wins of a player
    if player == None:
        await bot.say('```!gtaracewins <player>```')
    else:
        gtaCur.execute("""Select COALESCE(count(*),0), player.name
                            from raced
                            join player on player.rowid = raced.playerid
                            where rank = 1 AND
                                LOWER(player.name) like '%""" + player + """%'""")
        row = gtaCur.fetchone()
        await bot.say('```cs\nSpieler "%s" hat %s Rennen gewonnen.```' % (row[1], row[0]))
  
@bot.command()
async def gtavehicles(vehicle : str = ""):
    """Meistverwendesten Fahrzeuge"""
    #Returns top 7 used vehicles
    s = "```ml\n"
    if vehicle == "":
        s += "Die 7 meistverwendetsten Fahrzeuge\n"
        s += ('-' * 35)
        s += "\n"
        s += "| {:20s}| {:10s}|\n".format("Fahrzeug", "Anzahl")
        s += ('-' * 35)
        s += "\n"

    for row in gtaCur.execute("""Select vehicle, count(*) from (
                                    Select vehicle
                                    from raced
                                    where isdsq = 'False'
                                        AND vehicle like '%"""+vehicle+"""%'
                                    group by raceid, vehicle
                                )
                                group by vehicle
                                order by 2 desc
                                limit 7"""):
        if vehicle == "":
            s += '| {:20s}| {:10s}|\n'.format(str(row[0]), str(row[1]))
        else:
            s += 'Das Fahrzeug "%s" wurde %s mal verwendet.\n' % (row[0], row[1])
    s += '```'
    await bot.say(s)
  
@bot.command()
async def gtaplaylistwins():
    """Playlist Siege"""
    # Returns a list of players who won a playlist
    s = "```ml\n"
    s += "| {:20s}| {:8s}|\n".format("Spieler", "Siege")
    s += ('-' * 33)
    s += "\n"
    for row in gtaCur.execute("""
                    Select playername, count(*) as wins from
                        ( Select * from
                            ( Select playlistid, x.name as playlistname, player.name as playername, sum(points) as points from
                                ( Select *,
                                        CASE
                                        WHEN isdsq = 'True' OR isdnf = 'True' THEN 0
                                        WHEN rank = 1 THEN 15
                                        WHEN rank = 2 THEN 12
                                        WHEN rank = 3 THEN 10
                                        WHEN rank BETWEEN 4 AND 10 THEN 12 - rank
                                        ELSE 1
                                        END as points from
                                    playlist
                                    join race on race.playlistid = playlist.rowid
                                    join raced on raced.raceid = race.rowid
                                ) as x
                                join player on playerid = player.rowid
                                    group by playlistid, x.name, playername
                                    order by playlistid asc, points desc
                            ) group by playlistid
                              having max(points)
                        ) group by playername
                    order by wins desc"""):
        s += '| {:20s}| {:8s}|\n'.format(str(row[0]), str(row[1]))
    s += '```'
    await bot.say(s)
   
@bot.command()
async def gtaplaylist(playlist : str = ""):
    """Ergebnisse einer bestimmten Playliste"""
    
    if playlist == "":
        await bot.say("```!gtaplaylist <playlist>```")
    else:
        s = "```ml\n"
        s += "Ergebnis Playlist %s\n\n" % playlist
        s += "| {:5}| {:20s}| {:6s}|\n".format("Rang","Spieler", "Punkte")
        s += ('-' * 38)
        s += "\n"
        rank = 1
        prevPoints = -1
        for row in gtaCur.execute("""
                        Select player.name, sum(points) as points from (
                            Select *,
                                    CASE
                                    WHEN isdsq = 'True' OR isdnf = 'True' THEN 0
                                    WHEN rank = 1 THEN 15
                                    WHEN rank = 2 THEN 12
                                    WHEN rank = 3 THEN 10
                                    WHEN rank BETWEEN 4 AND 10 THEN 12 - rank
                                    ELSE 1
                                    END as points from
                                playlist
                                join race on race.playlistid = playlist.rowid
                                join raced on raced.raceid = race.rowid
                                where playlist.name='"""+playlist+"""'
                            ) as x
                            join player on playerid = player.rowid
                            group by player.name
                                order by points desc"""):
            if prevPoints == row[1]:
                rankMod += 1
            else:
                rankMod = 0
            s += "| {:5}| {:20s}| {:6s}|\n".format(str(rank-rankMod),str(row[0]), str(row[1]))
            prevPoints = row[1]
            rank += 1
        s += "```"
        await bot.say(s)
        
@bot.command()
async def updatetabletop(delete : bool = False, create : bool = False):
    """Updatet die Tabletop Datenbank"""
    try:
        global ttsCur
        global ttsConn
        await bot.say("Updating Tabletop Database ...")
        #ttsCur.close()
        #ttsConn.close()
        tts = sheets.Tabletop(delete, create, True, ttsConn)
        tts.update_database()
        await bot.say("Update finished!")
    except Exception as e:
        print(e)
        await bot.say("Error, check log :robot:")
        
    try:
        ttsConn = sqlite3.connect('db/tabletop.db')
        ttsCur = ttsConn.cursor()
    except Exception as e:
        print(e)

@bot.command()
async def updategta(delete : bool = False, create : bool = False):
    """Updatet die GTA Datenbank"""
    try:
        global gtaCur
        global gtaConn
        await bot.say("Updating Gta Database ...")
        #gtaCur.close()
        #gtaConn.close()
        gta = sheets.Gtasheet(delete, create, True, gtaConn)
        gta.update_database()
        await bot.say("Update finished!")
    except Exception as e:
        print(e)
        await bot.say("Error, check log :robot:")

    try:
        gtaConn = sqlite3.connect('db/gta.db')
        gtaCur = gtaConn.cursor()
    except Exception as e:
        print(e)

@bot.command(pass_context=True)
async def rammerdestages(ctx, chan:str = "GTA", extraOptions:str = ""):
    now = datetime.datetime.now()
    api = strawpoll.API()
    options = []
    
    if "," in extraOptions:
        for o in extraOptions.split(","):
            options.append(o)
    elif extraOptions != "":
        options.append(extraOptions)
    
    for channel in ctx.message.server.channels:
        if chan in channel.name: 
            for member in channel.voice_members:
                options.append(str(member).split("#")[0])
    if len(options) >= 2:  
        options.append("Alle sind fair gefahren ☺")
        poll = strawpoll.Poll("Rammer des Tages " + now.strftime("%Y-%m-%d"), options)
        poll.multi = True
        poll = await api.submit_poll(poll)
        await bot.upload("media/RammerDesTages.png")
        #await bot.say("Jetzt Abstimmen für den Rammer des Tages!")
        await bot.say(poll.url)
        # log poll url into a file
        with open("polls.txt", "a") as pollfile:
            pollfile.write(poll.url)
            pollfile.write("\n")
    else:
        await bot.say("Konnte die Umfrage nicht anlegen. Zu wenige Leute im Channel " + chan)
        
@bot.command(pass_context=True)
async def friends(ctx):
    """Freunde!"""
    user = discord.utils.get(ctx.message.server.members, name = 'Lefty')
    await bot.say(":robot: My only friend is " + user.mention)
        
@bot.command(pass_context=True, aliases=["addGif", "addgyf", "addGyf"])
async def addgif(ctx, url, game : str = "", comment : str = "", id : int = None):
    """Adds a gif to the database"""
    if url == None:
        await bot.say('```!addGif "<url>" "<game>" "<comment>"```')
    else:
        gifsCur.execute("""INSERT INTO gifs (url, game, comment, addedBy, addedOn) VALUES ('%s', '%s', '%s', '%s', current_timestamp)""" % (url, game, comment, ctx.message.author))
        lastid = gifsCur.lastrowid
        if id != None:
            gifsCur.execute("""Select ROWID from gifs where ROWID = %s""" % (id))
            row = gifsCur.fetchone()
            if row != None:
                gifsCur.execute("""INSERT INTO comboGifs (id1, id2) VALUES (%d, %d)""" % (lastid, id))
            else:
                await bot.say("Konnte kein Gif mit der id %d finden. Gif wurde **nicht** hinzugefügt!" % id)
                return
        gifsConn.commit()
        # get the inserted gif and format it
        outMessage = formatGifWithId(lastid)
        try:
            await bot.delete_message(ctx.message)
            await bot.say(outMessage)
        except discord.Forbidden as e:
            # when we don't have permissions to replace the message just print out a confirmation
            message = await bot.say("Gif hinzugefuegt")        
            await asyncio.sleep(6)
            await bot.delete_message(message)

def formatGifWithId(id : int):
    gifsCur.execute("""SELECT url, game, comment, addedBy, ROWID from gifs
                            WHERE ROWID = %s""" % (id))
    row = gifsCur.fetchone()
    return formatGif(row[0], row[1], row[2], row[3], row[4])
    
def formatGif(url, game, comment, addedBy, id):
    outStr = '```ml\n'
    if(comment != ""):
        outStr += '#%d: "%s"\n' % (id, comment)
    if(game != ""):
        outStr += "Spiel: " + game + "\n" 
    if(addedBy != ""):
        title = ['Dr. ', 'Meister ', 'Sir ', 'Mr. ', 'Lady ', '', '', '', '', '', '', '', '', '', '', '']
        # addedBy contains discord userid like Pacman#1234
        outStr += "Von " + random.choice(title) + addedBy.split("#")[0]
    outStr += '```'
    outStr += url
    
    # search for combo gifs
    for comboRow in gifsCur.execute("""Select id1, id2 from comboGifs
                                        where id2 = %s
                                        OR id1 = %s""" % (id, id)):
        if comboRow[0] == id:
            comboId = comboRow[1]
        else:
            comboId = comboRow[0]
        gifsCur2 = gifsConn.cursor()
        gifsCur2.execute("""Select url, comment, addedBy from gifs WHERE ROWID = %s """ % comboId)
        comboGif = gifsCur2.fetchone()
        if comboGif != None:
            outStr += '\n```ml\n'
            outStr += 'Das ist ein Combo Gif!\n'
            outStr += 'Von: %s\n' % comboGif[2].split("#")[0]
            outStr += '#%d: "%s"' % (comboId, comboGif[1])
            outStr += '```'
            outStr += comboGif[0]
    return outStr
        
@bot.command(aliases=["gifs", "showgif", "gyf"])
async def gif(search : str = ""):
    """Zeigt ein Gif aus der Datenbank an"""
    # Search for addedBy, game and comment
    
    try:
        # id suche
        id = int(search)
        gifsCur.execute("""SELECT url, game, comment, addedBy, ROWID from gifs
                            WHERE ROWID = """ + search)
    except ValueError:
        # string suche
        gifsCur.execute("""SELECT url, game, comment, addedBy, ROWID from gifs
                            WHERE ROWID IN
                                (Select ROWID from gifs
                                    where """ #LOWER(addedBy) like '%"""+search.lower()+"""%' OR 
                                     """LOWER(game) like '%"""+search.lower()+"""%' OR
                                        LOWER(comment) like '%""" + search.lower() + """%'
                                    ORDER BY RANDOM() LIMIT 1)""")
    row = gifsCur.fetchone()
    
    if(row != None):
        outStr = formatGif(row[0], row[1], row[2], row[3], row[4])
        
        await bot.say(outStr)
    else:
        await bot.say("Kein Gif zu '%s' gefunden.\nStattdessen gibt es :cake:." % search)        

@bot.command()
async def gifstats():
    gifsCur.execute("""Select count(*) from gifs""")
    row = gifsCur.fetchone()
    
    s = '```ml\n'
    s += "Anzahl an Gifs: %s\n\n" % row[0]
    s += "| {:20}| {:8s}|\n".format("Name","Anzahl")
    s += ('-' * 33)
    s += "\n"
    for row in gifsCur.execute("""SELECT addedBy, count(*)
                        from gifs
                        group by addedBy
                        order by 2 desc"""):
        s += "| {:20}| {:<8}|\n".format(row[0].split("#")[0], row[1])
    s += '```'
    await bot.say(s)

@bot.command(aliases=["listgifs", "listgif", "searchgifs"])
async def searchgif(searchterm : str = ""):
    """Zeigt ein Gif aus der Datenbank an"""
    # Search for gifs and show a list
    foundgif = False
    outStr = '```ml\n'
    outStr += "Folgende Gifs wurden gefunden:\n"
    outStr += "| {:6}| {:<15s}| {:<45s}| {:<10s}\n".format("ID","Spieler","Name", "Spiel")
    outStr += ('-' * 84)
    outStr += "\n"
    counter = 0
    for gif in gifsCur.execute("""Select game, comment, addedBy, ROWID from gifs
                                where """ #LOWER(addedBy) like '%""" + searchterm.lower() + """%' OR 
                                    """LOWER(game) like '%""" + searchterm.lower() + """%' OR
                                    LOWER(comment) like '%""" + searchterm.lower() + """%'"""):
        outStr += "| {:6}| {:<15.16}| {:<45.44}| {:<10.10s}\n".format("#"+str(gif[3]), str(gif[2]).split("#")[0], str(gif[1]), str(gif[0]))
        foundgif = True
        counter += 1
        if(counter >= 15):
            outStr += "Es wurden zu viele Gifs gefunden, bitte genauer suchen ..."
            break
    outStr += '```'
    if(foundgif):
        await bot.say(outStr)
    else:
        await bot.say("Kein Gif zu '" + searchterm + "' gefunden :sob:")
    
@bot.command(pass_context=True)
async def deletegif(ctx, id):
    """Löscht ein Gif mit der angegebenen ID. Kann nur vom ersteller gelöscht werden."""
    gifsCur.execute("""Select addedBy, url from gifs
                        where ROWID = """ + id)
    row = gifsCur.fetchone()
    
    if(row != None):
        if(str(ctx.message.author) == str(row[0])):
            # TODO: combo gifs löschen
            gifsCur.execute("""Delete from gifs
                                where ROWID = """ + id)
            with open("deletedgifs.txt", "a") as pollfile:
                pollfile.write("Deleting gif #" + row[0] + " - " + row[1])
                pollfile.write("\n")
            await bot.say("Gif #" + id + " gelöscht :put_litter_in_its_place: ")
        else:
            await bot.say(":no_entry_sign: " + ctx.message.author.mention + " Du bist nicht berechtigt Gif #" + id +" zu löschen :no_entry_sign:")
    else:
        bot.say("Gif mit der ID #" + id + " nicht gefunden.")
            
bot.run(token())