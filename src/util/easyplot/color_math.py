"""Pure color interpolation helpers shared by scientific and GTK views."""

def interpolate_color(color1, color2, fraction):
    return [ ( (x1 + fraction * (x2 - x1))) for (x1, x2) in zip(color1, color2)]

def get_color(value, color_map):#, factor = 2):

    if value == float('inf'):
        return [1,1,1]
    #value = (value+1)/factor

    cutoffs = list(color_map.keys())
    color_list = list(color_map.values())
    counter = 0

    #print(value)



    for cutoff, color in color_map.items():

        if value <= cutoff :

            fraction = (value -  cutoffs[counter-1]) / ( cutoff - cutoffs[counter-1])


            color1  = color_list[counter-1]
            color2  = color_list[counter]
            #
            #
            #
            #
            #
            color = interpolate_color(color1, color2, fraction)
            #color = [0,0,0]

            #color[0] = color[0]
            #color[1] = color[1]
            #color[2] = color[2]
            #print(value, cutoff, fraction,color )

            return color
        else:
            pass
            #print(value, cutoff)#, fraction,color )
        counter +=1

def bilinear_interpolation(c1, c2, c3, c4, tx, ty):
    return (
        int((1 - tx) * (1 - ty) * c1[0] + tx * (1 - ty) * c2[0] + (1 - tx) * ty * c4[0] + tx * ty * c3[0]),
        int((1 - tx) * (1 - ty) * c1[1] + tx * (1 - ty) * c2[1] + (1 - tx) * ty * c4[1] + tx * ty * c3[1]),
        int((1 - tx) * (1 - ty) * c1[2] + tx * (1 - ty) * c2[2] + (1 - tx) * ty * c4[2] + tx * ty * c3[2]),
        int((1 - tx) * (1 - ty) * c1[3] + tx * (1 - ty) * c2[3] + (1 - tx) * ty * c4[3] + tx * ty * c3[3])
    )

def expand_array_size (norm_data):
    """
    this function receives an i x j matrix and transforms it into an
    i+2 x j+2 matrix. the original matrix is ​​in the middle of the new
    matrix, so the added elements are on the edges. they will be
    important for the interpolation of points when the smooth function
    is used in ImagePlot.


       extra column /extra row
         |
       |---|---|---|---|---|
     --| x | x | x | x | x |
       |---|---|---|---|---|
       | x |###|###|###| x |
       |---|---|---|---|---|
       | x |###|###|###| x |
       |---|---|---|---|---|
       | x | x | x | x | x |--
       |---|---|---|---|---|
                         |
                       extra column /extra row

    ### = elements in original matrix
    x   = new elements

    -It's not a very efficient algorithm, but it works well
    """
    size_x = len(norm_data)
    size_y = len(norm_data[0])
    #print('expanded matrix')
    bigmatrix = []#[None]*size_x+2
    for k in range (0, size_x+2):
        bigmatrix.append([])
        for column in range(0,  size_y+2):
            bigmatrix[k].append(0)
    #pprint (bigmatrix )
    for k in range (0, size_x+2):
        for column in range(0,  size_y+2):

            #    extra column /extra row
            #      |
            #    |---|---|---|---|---|
            #  --|XXX|   |   |   |   |
            #    |---|---|---|---|---|
            #    |   |###|###|###|   |
            #    |---|---|---|---|---|
            #    |   |###|###|###|   |
            #    |---|---|---|---|---|
            #    |   |   |   |   |   |--
            #    |---|---|---|---|---|
            #                      |
            #                    extra column /extra row

            if   k == 0 and column == 0:
                bigmatrix[k][column] = norm_data[0][0]

            elif k == 0 and column == 1:
                bigmatrix[k][column] = norm_data[0][0]

            elif k == 1 and column == 0:
                bigmatrix[k][column] = norm_data[0][0]


            #    extra column /extra row
            #      |
            #    |---|---|---|---|---|
            #  --|   |   |   |   |   |
            #    |---|---|---|---|---|
            #    |   |###|###|###|   |
            #    |---|---|---|---|---|
            #    |   |###|###|###|   |
            #    |---|---|---|---|---|
            #    |   |   |   |   |XXX|--
            #    |---|---|---|---|---|
            #                      |
            #                    extra column /extra row

            elif k == size_x+1   and column == size_y+1 :
                bigmatrix[k][column] = norm_data[size_x-1][size_y-1]

            elif k == size_x   and column == size_y+1 :
                bigmatrix[k][column] = norm_data[size_x-1][size_y-1]

            elif k == size_x+1    and column == size_y :
                bigmatrix[k][column] = norm_data[size_x-1][size_y-1]


            #    extra column /extra row
            #      |
            #    |---|---|---|---|---|
            #  --|   |XXX|XXX|XXX|   |
            #    |---|---|---|---|---|
            #    |   |###|###|###|   |
            #    |---|---|---|---|---|
            #    |   |###|###|###|   |
            #    |---|---|---|---|---|
            #    |   |   |   |   |   |--
            #    |---|---|---|---|---|
            #                      |
            #                    extra column /extra row

            elif k == 0 and   size_y+1 > column > 0  :
                bigmatrix[k][column] = norm_data[0][column-1]


            #    extra column /extra row
            #      |
            #    |---|---|---|---|---|
            #  --|   |   |   |   |   |
            #    |---|---|---|---|---|
            #    |XXX|###|###|###|   |
            #    |---|---|---|---|---|
            #    |XXX|###|###|###|   |
            #    |---|---|---|---|---|
            #    |   |   |   |   |   |--
            #    |---|---|---|---|---|
            #                      |
            #                    extra column /extra row

            elif size_x+1 > k > 0 and column == 0:
                bigmatrix[k][column] = norm_data[k-1][0]


            #---------------------------------------------------
            #    extra column /extra row
            #      |
            #    |---|---|---|---|---|
            #  --|   |   |   |   |   |
            #    |---|---|---|---|---|
            #    |   |###|###|###|xxx|
            #    |---|---|---|---|---|
            #    |   |###|###|###|xxx|
            #    |---|---|---|---|---|
            #    |   |   |   |   |   |--
            #    |---|---|---|---|---|
            #                      |
            #                    extra column /extra row

            elif size_x+1 > k > 0 and size_y+1 == column:
                bigmatrix[k][column] = norm_data[k-1][size_y-1]
            #---------------------------------------------------

            #---------------------------------------------------
            #    extra column /extra row
            #      |
            #    |---|---|---|---|---|
            #  --|   |   |   |   |   |
            #    |---|---|---|---|---|
            #    |   |###|###|###|   |
            #    |---|---|---|---|---|
            #    |   |###|###|###|   |
            #    |---|---|---|---|---|
            #    |   |xxx|xxx|xxx|   |--
            #    |---|---|---|---|---|
            #                      |
            #                    extra column /extra row

            elif k == size_x+1 and size_y  > column> 0:
                bigmatrix[k][column] = norm_data[k-2][column-1]
            #---------------------------------------------------


            elif   k == 0        and column == size_y+1:
                bigmatrix[k][column] = norm_data[0][column-2]

            elif k == size_x+1 and column == 0:
                bigmatrix[k][column] = norm_data[k-2][0]

            else:
                bigmatrix[k][column] = norm_data[k-1][column-1]
    return bigmatrix
