let i = io.connect('http://' + document.domain + ':' + location.port);

let chatMessages = []

i.on('chatRedirect', (res)=>{console.log(res)})
i.on('userJoined', (res)=>{console.log(res)})
i.on('newMessage', (res)=>{
    chatMessages.push({
        name: res['userName'],
        img: res['imgData'],
        id: res['msgID'],
        caption: res['caption']
    })
    $('#messages-container').animate({scrollTop :  $('#messages-container').prop('scrollHeight')}, 750)
})

function joinChat() {
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.has('chat'))
        appV.chatID = parseInt( urlParams.get('chat'));
    else
    {
        alert("Please choose a chat.")
        document.location = "/"
    }

    i.emit('join', {'userName':appV.username,'token':getToken(), 'chatID':appV.chatID}, (res)=>{
        console.log(res)
        console.log(res.status)
        if ('error' in res)
        {
            alert(res['error'])  
            document.location = "/"
        }
        
        setToken(res['newToken'])
        var prevST, prevSH, newSH
        prevST = $("#messages-container").scrollTop()
        prevSH = $("#messages-container").prop('scrollHeight')

        fetchMessages(0, 15)

        setTimeout(()=>{
            console.log('start-sc')
            newSH = $("#messages-container").prop('scrollHeight')
            $('#messages-container').animate({scrollTop :  ((newSH-prevSH)+ prevST)}, 400)
        }, 400)
    })

}

function send() {
    if (tokenInRoute)
        return
    if (blank)
    {
        alert('Cannot send blank messages.')
        return
    }

    $.ajax({
        url: '/chat/send', // point to server-side URL
        cache: false,
        contentType: false,
        processData: false,
        data: JSON.stringify({'userName':appV.username,'token':getToken(), 
                                'chatID':appV.chatID, 'img':canvas.toDataURL('image/png'),
                                'caption':$('#caption-input').val() == ""?"None":$('#caption-input').val()}),
        type: 'POST', 
        error: (res)=>{
            if (res.status == 401)
                badToken()
            if ('error' in res)
                alert(res['error'])
        }
    }).done(function (res) {
        console.log(res)
        setToken(res['newToken'])
        appV.caption = false
        $('#caption-input').val('')
    }) 
}

function fetchMessages (offset, n) {
    if (tokenInRoute)
    {
        console.log('[chat.js] [fetch] Token in route, aborting.')
        return
    }

    $.ajax({
        url: '/chat/fetch', // point to server-side URL
        cache: false,
        contentType: false,
        processData: false,
        data: JSON.stringify({'userName':appV.username,'token':getToken(), 'chatID':appV.chatID, 'offset':offset, 'n':n}),
        type: 'POST', 
        async: false,
        error: (res)=>{
            if (res.status == 401)
                badToken()
            if ('error' in res)
                alert(res['error'])
        }
    }).done(function (res) {
        setToken(res['newToken'])

        var msgs = JSON.parse(res['msgs']).reverse()

        if (msgs.length == 0)
        {
            console.log('[chat.js] No more messages to fetch')
            return
        }

        console.log(res)

        var newBatch = []

        msgs.forEach(el => {
            newBatch.push({
                name: el['username'],
                img: el['img'],
                id: el['msgID'],
                caption: el['caption']
            })
        });

        chatMessages = [...newBatch, ...chatMessages]

        appV.messages = chatMessages

    }) 
}