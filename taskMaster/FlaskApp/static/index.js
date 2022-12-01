let errorBool = false

async function send_form(e, form){
    e.preventDefault()
    errorBool = false
    let error = document.getElementById('error')
    let result = document.getElementById('result')
    let url = '/add-tasks'
    formData = new FormData(form)
    error_check('min_mat_shape', 'max_mat_shape')
    error_check('min_deadline', 'max_deadline')
    data = await fetch(url, {
        method: 'post',
        body: formData,
    })
    // if the request produced no errors clear the error element
    if (!errorBool) {
        error.innerText = ''
    }
    result.innerText = await data.text()
}

function error_check(min, max) {
    // write in the error element and flip min and max
    if (parseInt(formData.get(min)) > parseInt(formData.get(max))){
        str = `${min} > ${max}. We flip the input.`.replaceAll('_', 'imum ')
        error.innerText = str.charAt(0).toUpperCase() + str.slice(1)
        a = formData.get(max)
        formData.set(max, formData.get(min))
        formData.set(min, a)
        document.getElementsByName(max)[0].value = formData.get(max)
        document.getElementsByName(min)[0].value = formData.get(min)
        errorBool = true
    }
}